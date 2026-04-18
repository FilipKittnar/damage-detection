import logging
from dataclasses import dataclass

import cv2
import numpy as np

from pipeline.models.interfaces import BoundingBox, Detector

logger = logging.getLogger(__name__)

_BOX_COLOR = (0, 0, 255)  # red in BGR
_BOX_THICKNESS = 2


@dataclass
class AnnotatedFrameData:
    annotated_frame: np.ndarray
    detections: list[BoundingBox]


class DamageStage:
    def __init__(self, detector: Detector):
        self._detector = detector

    def process(self, bgr_frame: np.ndarray) -> AnnotatedFrameData:
        detections = self._detector.detect(bgr_frame)
        annotated = bgr_frame.copy()
        for box in detections:
            cv2.rectangle(annotated, (box.x1, box.y1), (box.x2, box.y2), _BOX_COLOR, _BOX_THICKNESS)
        logger.debug("damage_stage_done", extra={"detections": len(detections)})
        return AnnotatedFrameData(annotated_frame=annotated, detections=detections)
