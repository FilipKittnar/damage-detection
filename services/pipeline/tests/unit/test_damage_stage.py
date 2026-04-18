import numpy as np
import pytest
from unittest.mock import MagicMock

from pipeline.models.interfaces import BoundingBox
from pipeline.stages.damage_stage import DamageStage


def _make_frame(h=100, w=100):
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_damage_stage_draws_boxes_when_detected():
    mock_detector = MagicMock()
    mock_detector.detect.return_value = [
        BoundingBox(x1=10, y1=10, x2=50, y2=50, confidence=0.9, label="damage")
    ]
    stage = DamageStage(detector=mock_detector)
    frame = _make_frame()
    result = stage.process(frame)
    assert not np.array_equal(result.annotated_frame, frame), "Frame should have boxes drawn"
    assert len(result.detections) == 1


def test_damage_stage_returns_original_when_no_detections():
    mock_detector = MagicMock()
    mock_detector.detect.return_value = []
    stage = DamageStage(detector=mock_detector)
    frame = _make_frame()
    result = stage.process(frame)
    assert np.array_equal(result.annotated_frame, frame)
    assert len(result.detections) == 0


def test_damage_stage_calls_detector_with_frame():
    mock_detector = MagicMock()
    mock_detector.detect.return_value = []
    stage = DamageStage(detector=mock_detector)
    frame = _make_frame()
    stage.process(frame)
    mock_detector.detect.assert_called_once()
