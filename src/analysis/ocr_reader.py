"""
Optical Character Recognition (OCR) Module

Extracts text from captured ROIs using Tesseract OCR.
Reads game clock, CS, gold, and parses kill feed for events.
"""

import re
import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: pytesseract not available, OCR will not work")


class ObjectiveType(Enum):
    """Types of objectives that can be detected"""
    DRAGON = "dragon"
    BARON = "baron"
    HERALD = "herald"
    TOWER = "tower"
    INHIBITOR = "inhibitor"


@dataclass
class OCRResult:
    """Result from OCR operation"""
    text: str
    confidence: float
    processed: bool = True


@dataclass
class GameTime:
    """Represents game time"""
    minutes: int
    seconds: int

    def to_seconds(self) -> int:
        """Convert to total seconds"""
        return self.minutes * 60 + self.seconds

    def __str__(self) -> str:
        return f"{self.minutes}:{self.seconds:02d}"


@dataclass
class ObjectiveEvent:
    """Represents an objective kill event"""
    objective_type: ObjectiveType
    team: str  # "ally" or "enemy"
    timestamp: float
    game_time: Optional[GameTime] = None


class OCRReader:
    """
    OCR Reader for extracting text from game UI elements.

    Uses Tesseract OCR with preprocessing for better accuracy.
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize the OCR reader.

        Args:
            confidence_threshold: Minimum confidence for OCR results
        """
        self.confidence_threshold = confidence_threshold
        self.tesseract_available = TESSERACT_AVAILABLE

        # Tesseract configuration
        self.tesseract_config = r'--oem 3 --psm 7'  # Single line mode

        # Patterns for text extraction
        self.time_pattern = re.compile(r'(\d{1,2}):(\d{2})')
        self.number_pattern = re.compile(r'(\d+)')

        # Objective keywords
        self.objective_keywords = {
            ObjectiveType.DRAGON: ['dragon', 'drg'],
            ObjectiveType.BARON: ['baron', 'nashor'],
            ObjectiveType.HERALD: ['herald', 'rift'],
            ObjectiveType.TOWER: ['turret', 'tower'],
            ObjectiveType.INHIBITOR: ['inhibitor', 'inhib']
        }

    def preprocess_image(self, image: np.ndarray, for_numbers: bool = False) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.

        Args:
            image: Input image
            for_numbers: Whether preprocessing is for numeric text

        Returns:
            Preprocessed image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Increase contrast
        gray = cv2.equalizeHist(gray)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)

        if for_numbers:
            # For numbers, use adaptive thresholding
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        else:
            # For text, use Otsu's thresholding
            _, binary = cv2.threshold(
                denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

        # Dilate slightly to connect broken characters
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(binary, kernel, iterations=1)

        return dilated

    def read_text(self, image: np.ndarray, preprocess: bool = True) -> OCRResult:
        """
        Extract text from image.

        Args:
            image: Input image
            preprocess: Whether to preprocess the image

        Returns:
            OCRResult object
        """
        if not self.tesseract_available:
            return OCRResult(text="", confidence=0.0, processed=False)

        try:
            # Preprocess if requested
            if preprocess:
                processed_img = self.preprocess_image(image)
            else:
                processed_img = image

            # Run Tesseract
            text = pytesseract.image_to_string(
                processed_img,
                config=self.tesseract_config
            ).strip()

            # Get confidence (requires more detailed data)
            data = pytesseract.image_to_data(
                processed_img,
                output_type=pytesseract.Output.DICT,
                config=self.tesseract_config
            )

            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

            return OCRResult(
                text=text,
                confidence=avg_confidence,
                processed=preprocess
            )

        except Exception as e:
            print(f"OCR error: {e}")
            return OCRResult(text="", confidence=0.0, processed=preprocess)

    def read_game_time(self, image: np.ndarray) -> Optional[GameTime]:
        """
        Read game clock from image.

        Args:
            image: Image of game clock ROI

        Returns:
            GameTime object or None
        """
        result = self.read_text(image, preprocess=True)

        if result.confidence < self.confidence_threshold:
            return None

        # Parse time pattern
        match = self.time_pattern.search(result.text)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            return GameTime(minutes=minutes, seconds=seconds)

        return None

    def read_number(self, image: np.ndarray) -> Optional[int]:
        """
        Read a numeric value from image.

        Args:
            image: Image containing number

        Returns:
            Integer value or None
        """
        # Preprocess for numbers
        processed = self.preprocess_image(image, for_numbers=True)

        # Use digits-only configuration
        config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'

        if not self.tesseract_available:
            return None

        try:
            text = pytesseract.image_to_string(processed, config=config).strip()

            # Extract first number found
            match = self.number_pattern.search(text)
            if match:
                return int(match.group(1))

        except Exception as e:
            print(f"Error reading number: {e}")

        return None

    def read_cs(self, image: np.ndarray) -> Optional[int]:
        """
        Read CS (creep score) from image.

        Args:
            image: Image of CS counter

        Returns:
            CS value or None
        """
        return self.read_number(image)

    def read_gold(self, image: np.ndarray) -> Optional[int]:
        """
        Read gold amount from image.

        Args:
            image: Image of gold counter

        Returns:
            Gold value or None
        """
        return self.read_number(image)

    def parse_kill_feed(self, image: np.ndarray) -> List[ObjectiveEvent]:
        """
        Parse kill feed for objective events.

        Args:
            image: Image of kill feed ROI

        Returns:
            List of ObjectiveEvent objects
        """
        result = self.read_text(image, preprocess=True)

        if result.confidence < self.confidence_threshold:
            return []

        events = []
        text_lower = result.text.lower()

        # Check for objective keywords
        for obj_type, keywords in self.objective_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Determine team (simplified - would need more context in real implementation)
                    team = "ally" if "your team" in text_lower else "enemy"

                    events.append(ObjectiveEvent(
                        objective_type=obj_type,
                        team=team,
                        timestamp=cv2.getTickCount() / cv2.getTickFrequency()
                    ))
                    break

        return events

    def detect_objective_text(self, text: str) -> Optional[ObjectiveType]:
        """
        Detect objective type from text.

        Args:
            text: Text to analyze

        Returns:
            ObjectiveType or None
        """
        text_lower = text.lower()

        for obj_type, keywords in self.objective_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return obj_type

        return None


class MockOCRReader(OCRReader):
    """
    Mock OCR reader for testing without Tesseract.

    Returns synthetic data for testing purposes.
    """

    def __init__(self, confidence_threshold: float = 0.7):
        super().__init__(confidence_threshold)
        self.mock_game_time = GameTime(minutes=15, seconds=30)
        self.mock_cs = 150
        self.mock_gold = 8500

    def read_game_time(self, image: np.ndarray) -> Optional[GameTime]:
        """Return mock game time"""
        self.mock_game_time.seconds += 1
        if self.mock_game_time.seconds >= 60:
            self.mock_game_time.seconds = 0
            self.mock_game_time.minutes += 1
        return self.mock_game_time

    def read_cs(self, image: np.ndarray) -> Optional[int]:
        """Return mock CS"""
        self.mock_cs += 1
        return self.mock_cs

    def read_gold(self, image: np.ndarray) -> Optional[int]:
        """Return mock gold"""
        self.mock_gold += 20
        return self.mock_gold

    def parse_kill_feed(self, image: np.ndarray) -> List[ObjectiveEvent]:
        """Return empty list for mock"""
        return []


def create_ocr_reader(confidence_threshold: float = 0.7,
                     use_mock: bool = False) -> OCRReader:
    """
    Factory function to create appropriate OCR reader.

    Args:
        confidence_threshold: Minimum confidence for OCR results
        use_mock: Force use of mock reader for testing

    Returns:
        OCRReader instance
    """
    if use_mock or not TESSERACT_AVAILABLE:
        return MockOCRReader(confidence_threshold)
    else:
        return OCRReader(confidence_threshold)


# Testing
if __name__ == "__main__":
    import time

    # Create mock OCR reader for testing
    reader = create_ocr_reader(use_mock=True)

    print("Testing OCR Reader (Mock Mode)...")

    # Test game time reading
    for i in range(5):
        game_time = reader.read_game_time(None)
        if game_time:
            print(f"Game Time: {game_time}")
        time.sleep(0.5)

    # Test CS reading
    cs = reader.read_cs(None)
    print(f"CS: {cs}")

    # Test gold reading
    gold = reader.read_gold(None)
    print(f"Gold: {gold}")

    print("\nOCR Reader test complete")
