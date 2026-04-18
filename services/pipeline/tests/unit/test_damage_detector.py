import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from pipeline.models.interfaces import BoundingBox


def _make_mock_yolo_result(boxes_xyxy=None, confidences=None, labels=None):
    result = MagicMock()
    if boxes_xyxy is None:
        result.boxes.xyxy = MagicMock()
        result.boxes.xyxy.cpu.return_value.numpy.return_value = []
        result.boxes.conf = MagicMock()
        result.boxes.conf.cpu.return_value.numpy.return_value = []
        result.boxes.cls = MagicMock()
        result.boxes.cls.cpu.return_value.numpy.return_value = []
        result.boxes.xyxy.__len__ = lambda self: 0
    else:
        import numpy as np
        result.boxes.xyxy = MagicMock()
        result.boxes.xyxy.cpu.return_value.numpy.return_value = np.array(boxes_xyxy)
        result.boxes.conf = MagicMock()
        result.boxes.conf.cpu.return_value.numpy.return_value = np.array(confidences or [])
        result.boxes.cls = MagicMock()
        result.boxes.cls.cpu.return_value.numpy.return_value = np.array(labels or [])
        result.boxes.xyxy.__len__ = lambda self: len(boxes_xyxy)
    return result


def test_damage_detector_returns_bounding_boxes():
    with patch("pipeline.models.yolov8.damage_detector.YOLO") as MockYOLO:
        mock_model = MagicMock()
        mock_result = _make_mock_yolo_result(
            boxes_xyxy=[[10, 20, 100, 80]],
            confidences=[0.87],
            labels=[0],
        )
        mock_model.return_value = [mock_result]
        MockYOLO.return_value = mock_model

        from pipeline.models.yolov8.damage_detector import YoloV8DamageDetector
        detector = YoloV8DamageDetector(model_path="fake.pt", confidence=0.45)
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        boxes = detector.detect(img)

    assert len(boxes) == 1
    assert isinstance(boxes[0], BoundingBox)
    assert boxes[0].x1 == 10
    assert boxes[0].confidence == pytest.approx(0.87, abs=0.01)


def test_damage_detector_returns_empty_on_no_detections():
    with patch("pipeline.models.yolov8.damage_detector.YOLO") as MockYOLO:
        mock_model = MagicMock()
        mock_result = _make_mock_yolo_result()
        mock_model.return_value = [mock_result]
        MockYOLO.return_value = mock_model

        from pipeline.models.yolov8.damage_detector import YoloV8DamageDetector
        detector = YoloV8DamageDetector(model_path="fake.pt", confidence=0.45)
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        boxes = detector.detect(img)

    assert boxes == []
