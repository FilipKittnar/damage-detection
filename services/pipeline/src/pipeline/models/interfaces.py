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


class Detector(ABC):
    @abstractmethod
    def detect(self, image: np.ndarray) -> list[BoundingBox]:
        ...
