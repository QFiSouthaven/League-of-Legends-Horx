"""
Game State Analysis Engine

Core engine that orchestrates capture, analysis, and communication.
Runs in isolated process for security and performance.
"""

import asyncio
import time
from typing import Dict, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.capture.capture_manager import create_capture_manager
from src.analysis.ocr_reader import create_ocr_reader, GameTime
from src.analysis.minimap_analyzer import create_minimap_analyzer
from src.features.strategic_features import StrategicAssistant
from src.ipc.ipc_handler import (
    IPCHandler, create_objective_event, create_minimap_event,
    create_informational_event
)
from src.config.config_loader import ConfigLoader


class AnalysisEngine:
    """
    Core analysis engine that coordinates all analysis tasks.

    This engine runs in a sandboxed process, receiving frame data
    and orchestrating various analysis sub-modules.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the analysis engine.

        Args:
            config_path: Optional path to configuration directory
        """
        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()

        # Initialize components
        self.capture_manager = None
        self.ocr_reader = None
        self.minimap_analyzer = None
        self.strategic_assistant = None
        self.ipc_handler = None

        # State
        self.running = False
        self.last_capture_time = 0
        self.capture_interval = 1.0 / self.config.capture_fps

        # Performance tracking
        self.frame_count = 0
        self.analysis_times = []

        print(f"Analysis Engine initialized")
        print(f"  Mode: {self.config.mode}")
        print(f"  Capture FPS: {self.config.capture_fps}")
        print(f"  Features: {[k for k, v in self.config.features.items() if v]}")

    async def initialize(self):
        """Initialize all components"""
        print("Initializing components...")

        # Create capture manager
        self.capture_manager = create_capture_manager(
            self.config.target_window_name,
            self.config.rois,
            use_fallback=True  # Use fallback for testing
        )

        # Find game window
        if not self.capture_manager.find_game_window():
            print("Warning: Game window not found, continuing with fallback")

        # Create OCR reader
        self.ocr_reader = create_ocr_reader(
            confidence_threshold=self.config.ocr_confidence_threshold,
            use_mock=True  # Use mock for testing
        )

        # Create minimap analyzer
        self.minimap_analyzer = create_minimap_analyzer(use_mock=True)

        # Create strategic assistant
        self.strategic_assistant = StrategicAssistant(self.config)

        # Initialize IPC handler
        self.ipc_handler = IPCHandler(
            host=self.config.ipc_host,
            port=self.config.ipc_port,
            jitter_ranges=self.config.jitter_ranges
        )

        await self.ipc_handler.start()

        print("All components initialized")

    async def run(self):
        """Main analysis loop"""
        self.running = True

        print("Analysis engine running...")

        try:
            while self.running:
                current_time = time.time()

                # Check if it's time to capture
                if current_time - self.last_capture_time >= self.capture_interval:
                    await self._process_frame()
                    self.last_capture_time = current_time

                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.01)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await self.shutdown()

    async def _process_frame(self):
        """Process a single frame"""
        start_time = time.time()

        try:
            # Check if game is still running
            if not self.capture_manager.is_game_running():
                print("Game window closed, stopping engine")
                self.running = False
                return

            # Capture ROIs based on enabled features
            rois_to_capture = self._get_required_rois()
            frames = self.capture_manager.capture_specific_rois(rois_to_capture)

            # Process each ROI
            ocr_data = {}

            # Process game clock
            if "game_clock" in frames:
                game_time = self.ocr_reader.read_game_time(frames["game_clock"].image)
                if game_time:
                    ocr_data["game_time"] = game_time

            # Process CS
            if "player_cs" in frames:
                cs = self.ocr_reader.read_cs(frames["player_cs"].image)
                if cs is not None:
                    ocr_data["cs"] = cs

            # Process gold
            if "player_gold" in frames:
                gold = self.ocr_reader.read_gold(frames["player_gold"].image)
                if gold is not None:
                    ocr_data["gold"] = gold

            # Process kill feed for objectives
            if "kill_feed" in frames:
                objective_events = self.ocr_reader.parse_kill_feed(frames["kill_feed"].image)
                if objective_events:
                    ocr_data["objective_events"] = objective_events

                    # Send objective timer events
                    for event in objective_events:
                        timer = self.strategic_assistant.objective_timers.add_objective_event(event)
                        if timer:
                            ipc_event = create_objective_event(
                                objective_name=event.objective_type.value,
                                respawn_time=timer.respawn_time
                            )
                            await self.ipc_handler.send_event(ipc_event)

            # Update strategic assistant with OCR data
            self.strategic_assistant.process_ocr_data(ocr_data)

            # Process minimap
            if "minimap" in frames:
                threats = self.minimap_analyzer.analyze(frames["minimap"].image)

                # Process threats and send alerts
                alerts = self.strategic_assistant.process_minimap_data(threats)

                for alert in alerts:
                    ipc_event = create_minimap_event(
                        enemy_location=alert["position"],
                        confidence=alert["confidence"]
                    )
                    await self.ipc_handler.send_event(ipc_event)

            # Send periodic state updates (every 5 seconds)
            if self.frame_count % (self.config.capture_fps * 5) == 0:
                state = self.strategic_assistant.get_state()
                await self.ipc_handler.send_direct({
                    "type": "state_update",
                    "state": state
                })

            self.frame_count += 1

            # Track performance
            analysis_time = time.time() - start_time
            self.analysis_times.append(analysis_time)

            # Log performance periodically
            if self.frame_count % 100 == 0:
                avg_time = sum(self.analysis_times) / len(self.analysis_times)
                print(f"Performance: {self.frame_count} frames, "
                      f"avg analysis time: {avg_time*1000:.2f}ms, "
                      f"FPS: {self.capture_manager.get_fps():.2f}")
                self.analysis_times = []

        except Exception as e:
            print(f"Error processing frame: {e}")
            import traceback
            traceback.print_exc()

    def _get_required_rois(self) -> list:
        """
        Get list of ROIs needed based on enabled features.

        Returns:
            List of ROI names to capture
        """
        rois = ["game_clock"]  # Always capture game clock

        if self.config.features.get("objective_timers", False):
            rois.append("kill_feed")

        if self.config.features.get("cs_tracker", False):
            rois.append("player_cs")

        if self.config.features.get("purchase_suggestions", False):
            rois.append("player_gold")

        if self.config.features.get("map_awareness", False):
            rois.append("minimap")

        return rois

    async def shutdown(self):
        """Clean shutdown"""
        print("Shutting down analysis engine...")

        self.running = False

        if self.ipc_handler:
            await self.ipc_handler.stop()

        if self.capture_manager:
            self.capture_manager.cleanup()

        print("Analysis engine stopped")


async def main():
    """Main entry point for analysis engine"""
    print("="*60)
    print("LOL-HORX Analysis Engine")
    print("="*60)

    # Create and initialize engine
    engine = AnalysisEngine()
    await engine.initialize()

    # Run the engine
    await engine.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEngine stopped by user")
