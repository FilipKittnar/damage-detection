"""
Contract test for POST /v1/blur.
Requires the plate-blurring service running at PLATE_BLURRING_URL (default http://localhost:8001).
Skip automatically if service is not reachable.
"""
import base64
import os
import pytest
import httpx
import numpy as np
import cv2

BLURRING_URL = os.getenv("PLATE_BLURRING_URL", "http://localhost:8001")


def _make_jpeg_with_plate() -> bytes:
    """Create a synthetic 480x640 BGR image with a white rectangle simulating a licence plate."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(img, (100, 200), (300, 250), (255, 255, 255), -1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


@pytest.fixture(scope="module")
def client():
    try:
        resp = httpx.get(f"{BLURRING_URL}/health", timeout=3)
        if resp.status_code != 200:
            pytest.skip("plate-blurring service not healthy")
    except Exception:
        pytest.skip("plate-blurring service not reachable")
    return httpx.Client(base_url=BLURRING_URL, timeout=30)


def test_blur_returns_200_with_required_fields(client):
    jpeg = _make_jpeg_with_plate()
    resp = client.post(
        "/v1/blur",
        files={"file": ("frame.jpg", jpeg, "image/jpeg")},
        data={"job_id": "test-contract-job", "frame_index": "0"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "image_b64" in body
    assert "plates_detected" in body
    assert "bounding_boxes" in body
    assert isinstance(body["plates_detected"], int)
    assert len(body["image_b64"]) > 0


def test_blur_returns_image_bytes(client):
    jpeg = _make_jpeg_with_plate()
    resp = client.post(
        "/v1/blur",
        files={"file": ("frame.jpg", jpeg, "image/jpeg")},
        data={"job_id": "test-contract-job", "frame_index": "1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    decoded = base64.b64decode(body["image_b64"])
    assert len(decoded) > 0
    arr = np.frombuffer(decoded, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    assert img is not None
    assert img.shape[0] > 0 and img.shape[1] > 0


def test_blur_missing_file_returns_422(client):
    resp = client.post(
        "/v1/blur",
        data={"job_id": "test-job", "frame_index": "0"},
    )
    assert resp.status_code == 422
