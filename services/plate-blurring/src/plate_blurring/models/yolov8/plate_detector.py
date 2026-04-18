import logging

import cv2
import numpy as np

from plate_blurring.models.interfaces import BoundingBox, PlateDetector

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None  # type: ignore[assignment,misc]


class YoloV8PlateDetector(PlateDetector):
    def __init__(self, model_path: str, confidence: float, blur_kernel_size: int):
        if YOLO is None:
            raise RuntimeError("ultralytics is not installed")
        self._model = YOLO(model_path)
        self._confidence = confidence
        self._blur_kernel_size = blur_kernel_size

    def detect_and_blur(self, image: np.ndarray) -> tuple[np.ndarray, list[BoundingBox]]:
        results = self._model(image, conf=self._confidence, verbose=False)
        blurred = image.copy()
        boxes: list[BoundingBox] = []
        for result in results:
            xyxy = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            for i in range(len(xyxy)):
                x1, y1, x2, y2 = int(xyxy[i][0]), int(xyxy[i][1]), int(xyxy[i][2]), int(xyxy[i][3])
                roi = blurred[y1:y2, x1:x2]
                ksize = self._blur_kernel_size
                blurred[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (ksize, ksize), 0)
                boxes.append(BoundingBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=float(confs[i]),
                    label="licence_plate",
                ))
        logger.debug("plate_detection_done", extra={"plates": len(boxes)})
        return blurred, boxes
