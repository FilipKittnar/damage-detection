import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FrameData:
    frame_index: int
    timestamp_sec: float
    bgr_array: np.ndarray


def extract_frames(video_path: Path, fps: float) -> Generator[FrameData, None, None]:
    cap = cv2.VideoCapture(str(video_path))
    try:
        source_fps = cap.get(cv2.CAP_PROP_FPS) or fps
        frame_skip = max(1, math.floor(source_fps / fps))
        current_index = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if current_index % frame_skip == 0:
                timestamp = current_index / source_fps
                yield FrameData(
                    frame_index=current_index,
                    timestamp_sec=timestamp,
                    bgr_array=frame,
                )
            current_index += 1
    finally:
        cap.release()
        logger.debug("frame_extraction_complete", extra={"video": str(video_path)})
