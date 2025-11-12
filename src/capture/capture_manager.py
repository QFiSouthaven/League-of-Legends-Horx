"""
Secure Screen Capture Module

Implements high-performance, window-specific capture for the League of Legends client.
Captures only essential UI elements defined by ROIs, with all processing done in-memory.
"""

import time
import numpy as np
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import cv2

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("Warning: mss not available, screen capture will be limited")

try:
    # Windows-specific imports
    import win32gui
    import win32ui
    import win32con
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    print("Warning: Windows-specific capture not available")


@dataclass
class CaptureFrame:
    """Represents a captured frame with metadata"""
    region_name: str
    image: np.ndarray
    timestamp: float
    resolution: Tuple[int, int]


class CaptureManager:
    """
    Manages secure screen capture for League of Legends.

    Features:
    - Window-specific capture (only LoL client)
    - ROI-based capture (only essential UI elements)
    - In-memory processing (no disk writes)
    - Performance monitoring
    """

    def __init__(self, target_window_name: str, rois: Dict):
        """
        Initialize the capture manager.

        Args:
            target_window_name: Name of the window to capture
            rois: Dictionary of ROI configurations
        """
        self.target_window_name = target_window_name
        self.rois = rois
        self.window_handle = None
        self.sct = None

        # Performance tracking
        self.frame_count = 0
        self.last_fps_check = time.time()
        self.current_fps = 0

        # Initialize capture system
        self._initialize_capture()

    def _initialize_capture(self):
        """Initialize the screen capture system"""
        if MSS_AVAILABLE:
            self.sct = mss.mss()
            print("MSS capture initialized")
        else:
            print("No capture system available")

    def find_game_window(self) -> bool:
        """
        Find and store the handle to the League of Legends window.

        Returns:
            True if window found, False otherwise
        """
        if not WINDOWS_AVAILABLE:
            print("Windows API not available, using full screen capture")
            return True

        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if self.target_window_name.lower() in window_text.lower():
                    windows.append(hwnd)

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            self.window_handle = windows[0]
            print(f"Found game window: {win32gui.GetWindowText(self.window_handle)}")
            return True
        else:
            print(f"Game window '{self.target_window_name}' not found")
            return False

    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the bounding rectangle of the game window.

        Returns:
            Tuple of (left, top, right, bottom) or None
        """
        if not WINDOWS_AVAILABLE or self.window_handle is None:
            return None

        try:
            rect = win32gui.GetWindowRect(self.window_handle)
            return rect
        except Exception as e:
            print(f"Error getting window rect: {e}")
            return None

    def capture_roi(self, roi_name: str) -> Optional[CaptureFrame]:
        """
        Capture a specific ROI from the game window.

        Args:
            roi_name: Name of the ROI to capture

        Returns:
            CaptureFrame object or None if capture failed
        """
        if roi_name not in self.rois:
            print(f"ROI '{roi_name}' not found in configuration")
            return None

        roi = self.rois[roi_name]

        # Get window position
        window_rect = self.get_window_rect()

        if window_rect and self.sct:
            # Calculate absolute screen coordinates
            left, top, right, bottom = window_rect

            monitor = {
                "left": left + roi.x,
                "top": top + roi.y,
                "width": roi.width,
                "height": roi.height
            }

            try:
                # Capture the region
                screenshot = self.sct.grab(monitor)

                # Convert to numpy array
                img = np.array(screenshot)

                # Convert BGRA to BGR (remove alpha channel)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # Update FPS counter
                self._update_fps()

                return CaptureFrame(
                    region_name=roi_name,
                    image=img,
                    timestamp=time.time(),
                    resolution=(roi.width, roi.height)
                )

            except Exception as e:
                print(f"Error capturing ROI '{roi_name}': {e}")
                return None

        return None

    def capture_all_rois(self) -> Dict[str, CaptureFrame]:
        """
        Capture all defined ROIs.

        Returns:
            Dictionary mapping ROI names to CaptureFrame objects
        """
        frames = {}

        for roi_name in self.rois.keys():
            frame = self.capture_roi(roi_name)
            if frame:
                frames[roi_name] = frame

        return frames

    def capture_specific_rois(self, roi_names: list) -> Dict[str, CaptureFrame]:
        """
        Capture specific ROIs by name.

        Args:
            roi_names: List of ROI names to capture

        Returns:
            Dictionary mapping ROI names to CaptureFrame objects
        """
        frames = {}

        for roi_name in roi_names:
            frame = self.capture_roi(roi_name)
            if frame:
                frames[roi_name] = frame

        return frames

    def _update_fps(self):
        """Update FPS counter"""
        self.frame_count += 1
        current_time = time.time()

        if current_time - self.last_fps_check >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_check)
            self.frame_count = 0
            self.last_fps_check = current_time

    def get_fps(self) -> float:
        """Get current capture FPS"""
        return self.current_fps

    def is_game_running(self) -> bool:
        """
        Check if the game window is still running.

        Returns:
            True if game is running, False otherwise
        """
        if not WINDOWS_AVAILABLE or self.window_handle is None:
            return True  # Assume running if we can't check

        try:
            return win32gui.IsWindow(self.window_handle) and win32gui.IsWindowVisible(self.window_handle)
        except Exception:
            return False

    def cleanup(self):
        """Clean up resources"""
        if self.sct:
            self.sct.close()
            print("Capture resources cleaned up")


class FallbackCaptureManager(CaptureManager):
    """
    Fallback capture manager for testing without game window.

    Generates synthetic frames for testing purposes.
    """

    def __init__(self, target_window_name: str, rois: Dict):
        """Initialize fallback capture manager"""
        super().__init__(target_window_name, rois)
        print("Using fallback capture manager (synthetic frames)")

    def find_game_window(self) -> bool:
        """Always return True for fallback"""
        return True

    def capture_roi(self, roi_name: str) -> Optional[CaptureFrame]:
        """Generate synthetic frame"""
        if roi_name not in self.rois:
            return None

        roi = self.rois[roi_name]

        # Create a blank image with some text
        img = np.zeros((roi.height, roi.width, 3), dtype=np.uint8)

        # Add some visual indication
        cv2.putText(
            img,
            f"{roi_name}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        # Add timestamp
        cv2.putText(
            img,
            f"{time.time():.2f}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (128, 128, 128),
            1
        )

        return CaptureFrame(
            region_name=roi_name,
            image=img,
            timestamp=time.time(),
            resolution=(roi.width, roi.height)
        )

    def is_game_running(self) -> bool:
        """Always return True for fallback"""
        return True


def create_capture_manager(target_window_name: str, rois: Dict,
                          use_fallback: bool = False) -> CaptureManager:
    """
    Factory function to create appropriate capture manager.

    Args:
        target_window_name: Name of the window to capture
        rois: Dictionary of ROI configurations
        use_fallback: Force use of fallback manager for testing

    Returns:
        CaptureManager instance
    """
    if use_fallback or not (MSS_AVAILABLE or WINDOWS_AVAILABLE):
        return FallbackCaptureManager(target_window_name, rois)
    else:
        return CaptureManager(target_window_name, rois)


# Testing
if __name__ == "__main__":
    from src.config.config_loader import load_default_config

    # Load configuration
    config = load_default_config()

    # Create capture manager
    manager = create_capture_manager(
        config.target_window_name,
        config.rois,
        use_fallback=True  # Use fallback for testing
    )

    # Find game window
    if manager.find_game_window():
        print("Testing capture...")

        # Capture a single ROI
        frame = manager.capture_roi("minimap")
        if frame:
            print(f"Captured {frame.region_name}: {frame.resolution}")

        # Capture all ROIs
        frames = manager.capture_all_rois()
        print(f"Captured {len(frames)} ROIs")

        # Show FPS
        time.sleep(1)
        print(f"Current FPS: {manager.get_fps():.2f}")

    manager.cleanup()
