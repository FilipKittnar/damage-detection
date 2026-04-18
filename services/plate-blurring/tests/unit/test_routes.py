import base64
import numpy as np
import cv2
import pytest
from unittest.mock import MagicMock

pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from plate_blurring.api.app import create_app
from plate_blurring.models.interfaces import BoundingBox


def _make_jpeg() -> bytes:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


@pytest.fixture
def client_with_model():
    mock_detector = MagicMock()
    blurred_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", blurred_img)
    mock_detector.detect_and_blur.return_value = (
        blurred_img,
        [BoundingBox(x1=10, y1=10, x2=50, y2=30, confidence=0.9, label="licence_plate")],
    )
    app = create_app(detector=mock_detector)
    return TestClient(app)


@pytest.fixture
def client_no_model():
    app = create_app(detector=None)
    return TestClient(app)


def test_blur_returns_200_with_valid_image(client_with_model):
    jpeg = _make_jpeg()
    resp = client_with_model.post(
        "/v1/blur",
        files={"file": ("frame.jpg", jpeg, "image/jpeg")},
        data={"job_id": "test-job", "frame_index": "0"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "image_b64" in body
    assert body["plates_detected"] == 1
    assert len(body["bounding_boxes"]) == 1


def test_blur_missing_file_returns_422(client_with_model):
    resp = client_with_model.post(
        "/v1/blur",
        data={"job_id": "test-job", "frame_index": "0"},
    )
    assert resp.status_code == 422


def test_health_when_model_loaded_returns_200(client_with_model):
    resp = client_with_model.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


def test_health_when_no_model_returns_503(client_no_model):
    resp = client_no_model.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["model_loaded"] is False
