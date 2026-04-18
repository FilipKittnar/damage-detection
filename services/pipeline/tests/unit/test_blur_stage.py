import base64
import numpy as np
import cv2
import pytest
from unittest.mock import patch, MagicMock

from pipeline.stages.blur_stage import BlurStage, BlurServiceUnavailableError


def _make_jpeg() -> bytes:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _make_b64_jpeg() -> str:
    return base64.b64encode(_make_jpeg()).decode()


def test_blur_stage_returns_decoded_jpeg_on_success():
    response_b64 = _make_b64_jpeg()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "image_b64": response_b64,
        "plates_detected": 1,
        "bounding_boxes": [],
    }
    with patch("pipeline.stages.blur_stage.httpx.post", return_value=mock_response):
        stage = BlurStage(blurring_url="http://fake-blurring:8001")
        result = stage.process(_make_jpeg(), job_id="job1", frame_index=0)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_blur_stage_raises_on_503():
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.json.return_value = {"error": "model_unavailable"}
    with patch("pipeline.stages.blur_stage.httpx.post", return_value=mock_response):
        stage = BlurStage(blurring_url="http://fake-blurring:8001")
        with pytest.raises(BlurServiceUnavailableError):
            stage.process(_make_jpeg(), job_id="job1", frame_index=0)


def test_blur_stage_raises_on_non_200():
    mock_response = MagicMock()
    mock_response.status_code = 500
    with patch("pipeline.stages.blur_stage.httpx.post", return_value=mock_response):
        stage = BlurStage(blurring_url="http://fake-blurring:8001")
        with pytest.raises(BlurServiceUnavailableError):
            stage.process(_make_jpeg(), job_id="job1", frame_index=0)


def test_blur_stage_raises_on_connection_error():
    import httpx as httpx_module
    with patch("pipeline.stages.blur_stage.httpx.post", side_effect=httpx_module.ConnectError("down")):
        stage = BlurStage(blurring_url="http://fake-blurring:8001")
        with pytest.raises(BlurServiceUnavailableError):
            stage.process(_make_jpeg(), job_id="job1", frame_index=0)
