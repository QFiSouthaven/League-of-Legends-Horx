#!/usr/bin/env python3
"""
LOL-HORX Main Application Entry Point

This script is responsible for:
1. Creating the main application window
2. Spawning the isolated analysis engine as a sandboxed child process
3. Establishing the Inter-Process Communication (IPC) bridge to the frontend overlay
4. Managing the lifecycle of all components
"""

import sys
import os
import subprocess
import multiprocessing
import signal
import time
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_loader import ConfigLoader


class ApplicationManager:
    """
    Main application manager for LOL-HORX.

    Coordinates the Python backend and Electron frontend.
    """

    def __init__(self, config_path: str = None, dev_mode: bool = False):
        """
        Initialize the application manager.

        Args:
            config_path: Optional path to configuration directory
            dev_mode: Enable development mode features
        """
        self.config_path = config_path
        self.dev_mode = dev_mode

        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()

        # Process handles
        self.analysis_process = None
        self.electron_process = None

        # State
        self.running = False

        print("="*60)
        print("LOL-HORX - League of Legends Strategic Overlay")
        print("="*60)
        print(f"Mode: {self.config.mode}")
        print(f"Development Mode: {dev_mode}")
        print("="*60)

    def start(self):
        """Start the application"""
        print("\nStarting LOL-HORX...")

        self.running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Start analysis engine in separate process
            self._start_analysis_engine()

            # Give analysis engine time to start IPC server
            time.sleep(2)

            # Start Electron overlay
            self._start_electron_overlay()

            # Monitor processes
            self._monitor_processes()

        except KeyboardInterrupt:
            print("\n\nShutdown requested...")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def _start_analysis_engine(self):
        """Start the analysis engine in a sandboxed process"""
        print("\nStarting analysis engine...")

        if self.config.sandbox_enabled:
            # In production, this would use proper sandboxing
            # For now, we use a standard subprocess
            print("  Note: Sandboxing is enabled in config but using standard process")

        # Use multiprocessing for better isolation
        from src.analysis.engine import main as engine_main

        self.analysis_process = multiprocessing.Process(
            target=self._run_engine,
            name="AnalysisEngine",
            daemon=False
        )

        self.analysis_process.start()

        print(f"  Analysis engine started (PID: {self.analysis_process.pid})")

    def _run_engine(self):
        """Run the analysis engine (executed in child process)"""
        import asyncio
        from src.analysis.engine import main as engine_main

        # Run the async engine
        try:
            asyncio.run(engine_main())
        except KeyboardInterrupt:
            print("Analysis engine stopped")

    def _start_electron_overlay(self):
        """Start the Electron overlay"""
        print("\nStarting Electron overlay...")

        # Check if node_modules exists
        node_modules = Path(__file__).parent / "node_modules"
        if not node_modules.exists():
            print("  Warning: node_modules not found!")
            print("  Please run: npm install")
            print("  Continuing anyway...")

        # Find electron executable
        electron_path = self._find_electron()

        if not electron_path:
            print("  Error: Electron not found!")
            print("  Please run: npm install")
            return

        # Build command
        cmd = [electron_path, "."]
        if self.dev_mode:
            cmd.append("--dev")

        # Start Electron
        try:
            self.electron_process = subprocess.Popen(
                cmd,
                cwd=str(Path(__file__).parent),
                stdout=subprocess.PIPE if not self.dev_mode else None,
                stderr=subprocess.PIPE if not self.dev_mode else None
            )

            print(f"  Electron overlay started (PID: {self.electron_process.pid})")

        except FileNotFoundError:
            print(f"  Error: Could not start Electron")
            print(f"  Command: {' '.join(cmd)}")

    def _find_electron(self) -> str:
        """
        Find electron executable.

        Returns:
            Path to electron or None
        """
        base_path = Path(__file__).parent / "node_modules" / ".bin"

        # Try different possible locations
        candidates = [
            base_path / "electron",
            base_path / "electron.cmd",
            Path(__file__).parent / "node_modules" / "electron" / "dist" / "electron",
            "electron",  # Try system electron
            "npx electron"  # Try npx
        ]

        for candidate in candidates:
            if isinstance(candidate, Path) and candidate.exists():
                return str(candidate)

        # Try which/where
        try:
            result = subprocess.run(
                ["which", "electron"] if os.name != 'nt' else ["where", "electron"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass

        return None

    def _monitor_processes(self):
        """Monitor running processes"""
        print("\nApplication running. Press Ctrl+C to stop.\n")

        while self.running:
            time.sleep(1)

            # Check if processes are still running
            if self.analysis_process and not self.analysis_process.is_alive():
                print("\nWarning: Analysis engine stopped unexpectedly")
                self.running = False
                break

            if self.electron_process and self.electron_process.poll() is not None:
                print("\nElectron overlay closed")
                self.running = False
                break

    def stop(self):
        """Stop the application"""
        print("\nStopping LOL-HORX...")

        self.running = False

        # Stop Electron
        if self.electron_process:
            print("  Stopping Electron overlay...")
            try:
                self.electron_process.terminate()
                self.electron_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.electron_process.kill()
            print("  Electron overlay stopped")

        # Stop analysis engine
        if self.analysis_process:
            print("  Stopping analysis engine...")
            try:
                self.analysis_process.terminate()
                self.analysis_process.join(timeout=5)
            except:
                self.analysis_process.kill()
            print("  Analysis engine stopped")

        print("\nLOL-HORX stopped")

    def _signal_handler(self, signum, frame):
        """Handle signals for graceful shutdown"""
        print(f"\nReceived signal {signum}")
        self.running = False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LOL-HORX - League of Legends Strategic Overlay"
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration directory',
        default=None
    )

    parser.add_argument(
        '--dev',
        action='store_true',
        help='Enable development mode'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['standard', 'passive'],
        help='Operational mode',
        default=None
    )

    parser.add_argument(
        '--test-engine',
        action='store_true',
        help='Test analysis engine only (no Electron)'
    )

    args = parser.parse_args()

    # Create application manager
    app = ApplicationManager(
        config_path=args.config,
        dev_mode=args.dev
    )

    # Override mode if specified
    if args.mode:
        app.config_loader.set_operational_mode(args.mode)

    # Test mode: only run engine
    if args.test_engine:
        print("\nTest mode: Running analysis engine only")
        print("Press Ctrl+C to stop\n")
        app._start_analysis_engine()
        try:
            app.analysis_process.join()
        except KeyboardInterrupt:
            print("\nStopping...")
            app.analysis_process.terminate()
        return

    # Start full application
    app.start()


if __name__ == "__main__":
    # Ensure multiprocessing works correctly
    multiprocessing.freeze_support()

    main()
