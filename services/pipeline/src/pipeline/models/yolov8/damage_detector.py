import logging

import numpy as np

from pipeline.models.interfaces import BoundingBox, Detector

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None  # type: ignore[assignment,misc]


class YoloV8DamageDetector(Detector):
    def __init__(self, model_path: str, confidence: float):
        if YOLO is None:
            raise RuntimeError("ultralytics is not installed")
        self._model = YOLO(model_path)
        self._confidence = confidence

    def detect(self, image: np.ndarray) -> list[BoundingBox]:
        results = self._model(image, conf=self._confidence, verbose=False)
        boxes = []
        for result in results:
            xyxy = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            for i in range(len(xyxy)):
                x1, y1, x2, y2 = xyxy[i]
                boxes.append(BoundingBox(
                    x1=int(x1), y1=int(y1), x2=int(x2), y2=int(y2),
                    confidence=float(confs[i]),
                    label="damage",
                ))
        logger.debug("damage_detected", extra={"count": len(boxes)})
        return boxes
