import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from plate_blurring.models.interfaces import BoundingBox


def _make_mock_yolo_result(boxes_xyxy=None, confidences=None):
    result = MagicMock()
    if boxes_xyxy is None:
        result.boxes.xyxy.cpu.return_value.numpy.return_value = np.array([]).reshape(0, 4)
        result.boxes.conf.cpu.return_value.numpy.return_value = np.array([])
        result.boxes.__len__ = lambda self: 0
    else:
        result.boxes.xyxy.cpu.return_value.numpy.return_value = np.array(boxes_xyxy, dtype=float)
        result.boxes.conf.cpu.return_value.numpy.return_value = np.array(confidences or [])
        result.boxes.__len__ = lambda self: len(boxes_xyxy)
    return result


def test_plate_detector_blurs_detected_region():
    with patch("plate_blurring.models.yolov8.plate_detector.YOLO") as MockYOLO:
        mock_model = MagicMock()
        mock_result = _make_mock_yolo_result(
            boxes_xyxy=[[50, 50, 150, 100]],
            confidences=[0.92],
        )
        mock_model.return_value = [mock_result]
        MockYOLO.return_value = mock_model

        from plate_blurring.models.yolov8.plate_detector import YoloV8PlateDetector
        detector = YoloV8PlateDetector(model_path="fake.pt", confidence=0.45, blur_kernel_size=51)
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[50:100, 50:150] = 200
        blurred, boxes = detector.detect_and_blur(img)

    assert blurred is not None
    assert blurred.shape == img.shape
    region_original = img[50:100, 50:150]
    region_blurred = blurred[50:100, 50:150]
    assert not np.array_equal(region_original, region_blurred), "Plate region should be blurred"
    assert len(boxes) == 1
    assert isinstance(boxes[0], BoundingBox)


def test_plate_detector_returns_unchanged_image_when_no_plates():
    with patch("plate_blurring.models.yolov8.plate_detector.YOLO") as MockYOLO:
        mock_model = MagicMock()
        mock_result = _make_mock_yolo_result()
        mock_model.return_value = [mock_result]
        MockYOLO.return_value = mock_model

        from plate_blurring.models.yolov8.plate_detector import YoloV8PlateDetector
        detector = YoloV8PlateDetector(model_path="fake.pt", confidence=0.45, blur_kernel_size=51)
        img = np.full((200, 200, 3), 128, dtype=np.uint8)
        blurred, boxes = detector.detect_and_blur(img)

    assert np.array_equal(blurred, img)
    assert boxes == []
