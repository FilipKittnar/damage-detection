from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    label: str


class PlateDetector(ABC):
    @abstractmethod
    def detect_and_blur(self, image: np.ndarray) -> tuple[np.ndarray, list[BoundingBox]]:
        ...
