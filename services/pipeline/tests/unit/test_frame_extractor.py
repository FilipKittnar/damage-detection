from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

from pipeline.stages.frame_extractor import extract_frames, FrameData


def _make_mock_capture(fps: float, total_frames: int):
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.get.side_effect = lambda prop: {
        5: fps,   # cv2.CAP_PROP_FPS
        7: total_frames,  # cv2.CAP_PROP_FRAME_COUNT
    }.get(prop, 0)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_index = [0]

    def read_side_effect():
        idx = frame_index[0]
        frame_index[0] += 1
        if idx < total_frames:
            return True, frame.copy()
        return False, None

    cap.read.side_effect = read_side_effect
    return cap


def test_extract_frames_yields_correct_count():
    with patch("pipeline.stages.frame_extractor.cv2.VideoCapture") as MockCap:
        MockCap.return_value = _make_mock_capture(fps=30.0, total_frames=90)
        frames = list(extract_frames(Path("/fake/video.mp4"), fps=1.0))
    assert len(frames) == 3


def test_extract_frames_correct_indices():
    with patch("pipeline.stages.frame_extractor.cv2.VideoCapture") as MockCap:
        MockCap.return_value = _make_mock_capture(fps=30.0, total_frames=90)
        frames = list(extract_frames(Path("/fake/video.mp4"), fps=1.0))
    indices = [f.frame_index for f in frames]
    assert indices == [0, 30, 60]


def test_extract_frames_correct_timestamps():
    with patch("pipeline.stages.frame_extractor.cv2.VideoCapture") as MockCap:
        MockCap.return_value = _make_mock_capture(fps=30.0, total_frames=90)
        frames = list(extract_frames(Path("/fake/video.mp4"), fps=1.0))
    timestamps = [f.timestamp_sec for f in frames]
    assert timestamps == pytest.approx([0.0, 1.0, 2.0], abs=0.01)


def test_extract_frames_is_generator():
    with patch("pipeline.stages.frame_extractor.cv2.VideoCapture") as MockCap:
        MockCap.return_value = _make_mock_capture(fps=30.0, total_frames=30)
        result = extract_frames(Path("/fake/video.mp4"), fps=1.0)
    import inspect
    assert inspect.isgenerator(result)


def test_extract_frames_releases_capture():
    with patch("pipeline.stages.frame_extractor.cv2.VideoCapture") as MockCap:
        cap = _make_mock_capture(fps=30.0, total_frames=30)
        MockCap.return_value = cap
        list(extract_frames(Path("/fake/video.mp4"), fps=1.0))
    cap.release.assert_called_once()
