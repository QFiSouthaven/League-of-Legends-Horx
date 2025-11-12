"""
Configuration Loader Module

Secure configuration loader for the LOL-HORX application.
Responsible for loading ROI coordinates, application settings, and operational modes.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ROIConfig:
    """Region of Interest configuration"""
    x: int
    y: int
    width: int
    height: int
    description: str = ""


@dataclass
class AppConfig:
    """Main application configuration"""
    # Operational mode
    mode: str = "standard"  # "standard" or "passive"

    # IPC settings
    ipc_host: str = "127.0.0.1"
    ipc_port: int = 8765

    # Capture settings
    target_window_name: str = "League of Legends (TM) Client"
    capture_fps: int = 10  # Frames per second for capture

    # Analysis settings
    ocr_confidence_threshold: float = 0.7
    minimap_analysis_interval: float = 0.5  # seconds

    # Feature toggles
    features: Dict[str, bool] = field(default_factory=lambda: {
        "objective_timers": True,
        "cs_tracker": True,
        "purchase_suggestions": True,
        "map_awareness": True,
        "informational_hud": True
    })

    # Adaptive jitter ranges (in milliseconds)
    jitter_ranges: Dict[str, tuple] = field(default_factory=lambda: {
        "informational": (100, 300),
        "objective_timers": (50, 200),
        "minimap_alerts": (30, 80),
        "purchase_suggestions": (150, 400)
    })

    # Overlay settings
    overlay_opacity: float = 0.8
    overlay_scale: float = 1.0

    # Security settings
    sandbox_enabled: bool = True
    verify_config_signature: bool = False  # For production

    # ROIs
    rois: Dict[str, ROIConfig] = field(default_factory=dict)
    resolution: str = "1920x1080"
    scaling_factor: float = 1.0


class ConfigLoader:
    """Secure configuration loader"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration loader.

        Args:
            config_dir: Optional custom configuration directory
        """
        if config_dir is None:
            # Default to src/config directory
            self.config_dir = Path(__file__).parent
        else:
            self.config_dir = Path(config_dir)

        self.config: Optional[AppConfig] = None

    def load_config(self, config_file: str = "app_config.json") -> AppConfig:
        """
        Load application configuration from file.

        Args:
            config_file: Name of the configuration file

        Returns:
            AppConfig instance
        """
        config_path = self.config_dir / config_file

        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Create AppConfig from loaded data
            self.config = AppConfig(**config_data)
        else:
            # Use default configuration
            self.config = AppConfig()

        # Load ROIs
        self._load_rois()

        return self.config

    def _load_rois(self, roi_file: str = "rois.json") -> None:
        """
        Load ROI definitions from file.

        Args:
            roi_file: Name of the ROI configuration file
        """
        roi_path = self.config_dir / roi_file

        if not roi_path.exists():
            raise FileNotFoundError(f"ROI configuration file not found: {roi_path}")

        with open(roi_path, 'r') as f:
            roi_data = json.load(f)

        # Extract resolution and scaling
        self.config.resolution = roi_data.get("resolution", "1920x1080")

        # Parse ROIs
        for name, roi_config in roi_data.get("rois", {}).items():
            self.config.rois[name] = ROIConfig(**roi_config)

    def save_config(self, config_file: str = "app_config.json") -> None:
        """
        Save current configuration to file.

        Args:
            config_file: Name of the configuration file
        """
        if self.config is None:
            raise ValueError("No configuration loaded to save")

        config_path = self.config_dir / config_file

        # Convert dataclass to dict
        config_dict = {
            "mode": self.config.mode,
            "ipc_host": self.config.ipc_host,
            "ipc_port": self.config.ipc_port,
            "target_window_name": self.config.target_window_name,
            "capture_fps": self.config.capture_fps,
            "ocr_confidence_threshold": self.config.ocr_confidence_threshold,
            "minimap_analysis_interval": self.config.minimap_analysis_interval,
            "features": self.config.features,
            "jitter_ranges": self.config.jitter_ranges,
            "overlay_opacity": self.config.overlay_opacity,
            "overlay_scale": self.config.overlay_scale,
            "sandbox_enabled": self.config.sandbox_enabled,
            "verify_config_signature": self.config.verify_config_signature
        }

        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)

    def get_roi(self, roi_name: str) -> Optional[ROIConfig]:
        """
        Get a specific ROI configuration.

        Args:
            roi_name: Name of the ROI

        Returns:
            ROIConfig instance or None if not found
        """
        if self.config is None:
            raise ValueError("Configuration not loaded")

        return self.config.rois.get(roi_name)

    def get_scaled_roi(self, roi_name: str, current_resolution: tuple) -> Optional[tuple]:
        """
        Get ROI coordinates scaled to current resolution.

        Args:
            roi_name: Name of the ROI
            current_resolution: (width, height) tuple of current screen resolution

        Returns:
            Tuple of (x, y, width, height) scaled to current resolution
        """
        roi = self.get_roi(roi_name)
        if roi is None:
            return None

        # Calculate scaling factor based on resolution
        base_width = 1920  # Base resolution width from rois.json
        scale = current_resolution[0] / base_width

        return (
            int(roi.x * scale),
            int(roi.y * scale),
            int(roi.width * scale),
            int(roi.height * scale)
        )

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature_name: Name of the feature

        Returns:
            True if enabled, False otherwise
        """
        if self.config is None:
            raise ValueError("Configuration not loaded")

        return self.config.features.get(feature_name, False)

    def set_operational_mode(self, mode: str) -> None:
        """
        Set the operational mode (standard or passive).

        Args:
            mode: "standard" or "passive"
        """
        if mode not in ["standard", "passive"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'standard' or 'passive'")

        if self.config is None:
            raise ValueError("Configuration not loaded")

        self.config.mode = mode

        # In passive mode, disable certain proactive features
        if mode == "passive":
            self.config.features["map_awareness"] = False
            self.config.features["purchase_suggestions"] = False

    def verify_signature(self, config_file: str) -> bool:
        """
        Verify the signature of a configuration file.

        This is a placeholder for production signature verification.
        In production, this would use cryptographic signatures to ensure
        configuration files haven't been tampered with.

        Args:
            config_file: Name of the configuration file

        Returns:
            True if signature is valid, False otherwise
        """
        # TODO: Implement actual signature verification for production
        # For now, always return True
        return True


# Convenience function for quick loading
def load_default_config() -> AppConfig:
    """
    Load the default application configuration.

    Returns:
        AppConfig instance
    """
    loader = ConfigLoader()
    return loader.load_config()


if __name__ == "__main__":
    # Test the configuration loader
    loader = ConfigLoader()
    config = loader.load_config()

    print(f"Configuration loaded:")
    print(f"  Mode: {config.mode}")
    print(f"  IPC: {config.ipc_host}:{config.ipc_port}")
    print(f"  Target FPS: {config.capture_fps}")
    print(f"  ROIs loaded: {len(config.rois)}")

    # Test ROI access
    minimap_roi = loader.get_roi("minimap")
    if minimap_roi:
        print(f"\nMinimap ROI: {minimap_roi.x}, {minimap_roi.y}, "
              f"{minimap_roi.width}x{minimap_roi.height}")

    # Test scaled ROI
    scaled = loader.get_scaled_roi("minimap", (1280, 720))
    if scaled:
        print(f"Minimap ROI (scaled to 1280x720): {scaled}")
