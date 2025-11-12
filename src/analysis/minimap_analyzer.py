"""
Minimap Analysis Module

Detects enemy champion appearances and threats on the minimap using computer vision.
Uses template matching and color detection to identify new enemy positions.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass
import time


@dataclass
class MinimapThreat:
    """Represents a detected threat on the minimap"""
    position: Tuple[int, int]  # (x, y) on minimap
    threat_type: str  # "champion", "ward", "objective"
    confidence: float
    timestamp: float
    is_new: bool = True


@dataclass
class MinimapRegion:
    """Defines a region on the minimap"""
    name: str
    bounds: Tuple[int, int, int, int]  # (x, y, width, height)


class MinimapAnalyzer:
    """
    Analyzes the minimap to detect enemy champions and threats.

    Uses computer vision techniques:
    - Color thresholding for red (enemy) markers
    - Template matching for champion icons
    - Movement detection for new appearances
    """

    def __init__(self):
        """Initialize the minimap analyzer"""
        # Color ranges for enemy detection (HSV)
        # Red color range for enemy team
        self.enemy_color_lower1 = np.array([0, 100, 100])
        self.enemy_color_upper1 = np.array([10, 255, 255])
        self.enemy_color_lower2 = np.array([170, 100, 100])
        self.enemy_color_upper2 = np.array([180, 255, 255])

        # Tracking previous detections
        self.previous_threats: Set[Tuple[int, int]] = set()
        self.threat_history: List[MinimapThreat] = []
        self.last_analysis_time = 0

        # Detection parameters
        self.min_blob_size = 5  # Minimum pixels for a detection
        self.max_blob_size = 50  # Maximum pixels for a detection
        self.position_tolerance = 10  # Pixels tolerance for same position

        # Cooldown for same position alerts (seconds)
        self.alert_cooldown = 3.0

    def analyze(self, minimap_image: np.ndarray) -> List[MinimapThreat]:
        """
        Analyze minimap image for threats.

        Args:
            minimap_image: Image of the minimap ROI

        Returns:
            List of detected threats
        """
        current_time = time.time()
        self.last_analysis_time = current_time

        # Detect enemy markers
        enemy_positions = self._detect_enemy_markers(minimap_image)

        # Create threat objects
        threats = []
        for pos in enemy_positions:
            # Check if this is a new threat or moved threat
            is_new = self._is_new_threat(pos, current_time)

            threat = MinimapThreat(
                position=pos,
                threat_type="champion",
                confidence=0.8,  # Base confidence
                timestamp=current_time,
                is_new=is_new
            )

            threats.append(threat)

        # Update tracking
        self.previous_threats = set(enemy_positions)

        # Trim history
        self._cleanup_history(current_time)

        return threats

    def _detect_enemy_markers(self, image: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect enemy champion markers using color detection.

        Args:
            image: Minimap image

        Returns:
            List of (x, y) positions
        """
        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Create mask for red colors (enemy team)
        mask1 = cv2.inRange(hsv, self.enemy_color_lower1, self.enemy_color_upper1)
        mask2 = cv2.inRange(hsv, self.enemy_color_lower2, self.enemy_color_upper2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Morphological operations to clean up the mask
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        positions = []

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by size
            if self.min_blob_size <= area <= self.max_blob_size:
                # Get centroid
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    positions.append((cx, cy))

        return positions

    def _detect_champions_template(self, image: np.ndarray,
                                   templates: List[np.ndarray]) -> List[Tuple[int, int]]:
        """
        Detect champions using template matching.

        This is a more advanced method that requires champion icon templates.

        Args:
            image: Minimap image
            templates: List of champion icon templates

        Returns:
            List of (x, y) positions
        """
        positions = []

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        for template in templates:
            # Convert template to grayscale
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            # Apply template matching
            result = cv2.matchTemplate(gray, template_gray, cv2.TM_CCOEFF_NORMED)

            # Find matches above threshold
            threshold = 0.7
            locations = np.where(result >= threshold)

            for pt in zip(*locations[::-1]):
                positions.append(pt)

        return positions

    def _is_new_threat(self, position: Tuple[int, int], current_time: float) -> bool:
        """
        Check if a threat position is new or has moved significantly.

        Args:
            position: (x, y) position to check
            current_time: Current timestamp

        Returns:
            True if this is a new threat
        """
        # Check against previous threats
        for prev_pos in self.previous_threats:
            distance = self._calculate_distance(position, prev_pos)
            if distance < self.position_tolerance:
                # Same position, check cooldown
                return self._check_alert_cooldown(position, current_time)

        # New position
        return True

    def _check_alert_cooldown(self, position: Tuple[int, int], current_time: float) -> bool:
        """
        Check if enough time has passed since last alert for this position.

        Args:
            position: Position to check
            current_time: Current timestamp

        Returns:
            True if cooldown has passed
        """
        for threat in reversed(self.threat_history):
            distance = self._calculate_distance(position, threat.position)

            if distance < self.position_tolerance:
                time_since = current_time - threat.timestamp
                return time_since >= self.alert_cooldown

        return True

    def _calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """
        Calculate Euclidean distance between two positions.

        Args:
            pos1: First position
            pos2: Second position

        Returns:
            Distance in pixels
        """
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def _cleanup_history(self, current_time: float, max_age: float = 30.0):
        """
        Remove old threats from history.

        Args:
            current_time: Current timestamp
            max_age: Maximum age for history entries in seconds
        """
        self.threat_history = [
            threat for threat in self.threat_history
            if current_time - threat.timestamp < max_age
        ]

    def get_map_quadrant(self, position: Tuple[int, int],
                        map_size: Tuple[int, int]) -> str:
        """
        Get the map quadrant for a position.

        Args:
            position: (x, y) position on minimap
            map_size: (width, height) of minimap

        Returns:
            Quadrant name: "top-left", "top-right", "bottom-left", "bottom-right"
        """
        x, y = position
        width, height = map_size

        mid_x = width / 2
        mid_y = height / 2

        if x < mid_x and y < mid_y:
            return "top-left"
        elif x >= mid_x and y < mid_y:
            return "top-right"
        elif x < mid_x and y >= mid_y:
            return "bottom-left"
        else:
            return "bottom-right"

    def get_lane_region(self, position: Tuple[int, int],
                       map_size: Tuple[int, int]) -> str:
        """
        Estimate which lane a position is in.

        Args:
            position: (x, y) position on minimap
            map_size: (width, height) of minimap

        Returns:
            Lane name: "top", "jungle", "mid", "bot", "river"
        """
        x, y = position
        width, height = map_size

        # Normalize coordinates
        norm_x = x / width
        norm_y = y / height

        # Simple lane detection based on position
        # This is approximate and would need tuning for actual map

        # River diagonal
        if abs(norm_x - norm_y) < 0.2:
            return "river"

        # Top lane
        if norm_y < 0.3:
            return "top"

        # Bot lane
        if norm_y > 0.7:
            return "bot"

        # Lanes vs Jungle
        if norm_x < 0.3 or norm_x > 0.7 or norm_y < 0.3 or norm_y > 0.7:
            if norm_x + norm_y < 0.8 or norm_x + norm_y > 1.2:
                return "jungle"
            else:
                return "mid"

        return "jungle"

    def visualize_detections(self, image: np.ndarray,
                            threats: List[MinimapThreat]) -> np.ndarray:
        """
        Draw detected threats on the minimap image for debugging.

        Args:
            image: Minimap image
            threats: List of detected threats

        Returns:
            Image with visualizations
        """
        output = image.copy()

        for threat in threats:
            x, y = threat.position
            color = (0, 0, 255) if threat.is_new else (0, 165, 255)  # Red or Orange

            # Draw circle at threat position
            cv2.circle(output, (x, y), 8, color, 2)

            # Draw confidence
            conf_text = f"{threat.confidence:.2f}"
            cv2.putText(output, conf_text, (x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return output


class MockMinimapAnalyzer(MinimapAnalyzer):
    """
    Mock minimap analyzer for testing.

    Generates synthetic threat detections.
    """

    def __init__(self):
        super().__init__()
        self.threat_counter = 0

    def analyze(self, minimap_image: np.ndarray) -> List[MinimapThreat]:
        """Generate mock threats"""
        current_time = time.time()

        # Generate a threat every few calls
        self.threat_counter += 1

        if self.threat_counter % 10 == 0:
            # Random position
            height, width = minimap_image.shape[:2]
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)

            threat = MinimapThreat(
                position=(x, y),
                threat_type="champion",
                confidence=0.85,
                timestamp=current_time,
                is_new=True
            )

            return [threat]

        return []


def create_minimap_analyzer(use_mock: bool = False) -> MinimapAnalyzer:
    """
    Factory function to create appropriate minimap analyzer.

    Args:
        use_mock: Force use of mock analyzer for testing

    Returns:
        MinimapAnalyzer instance
    """
    if use_mock:
        return MockMinimapAnalyzer()
    else:
        return MinimapAnalyzer()


# Testing
if __name__ == "__main__":
    import time

    # Create mock analyzer
    analyzer = create_minimap_analyzer(use_mock=True)

    print("Testing Minimap Analyzer (Mock Mode)...")

    # Simulate minimap analysis
    dummy_image = np.zeros((260, 260, 3), dtype=np.uint8)

    for i in range(30):
        threats = analyzer.analyze(dummy_image)

        if threats:
            for threat in threats:
                print(f"Threat detected at {threat.position}, "
                      f"confidence: {threat.confidence:.2f}, "
                      f"new: {threat.is_new}")

        time.sleep(0.1)

    print("\nMinimap Analyzer test complete")
