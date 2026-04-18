"""
Contract test for GET /health.
Requires the plate-blurring service running at PLATE_BLURRING_URL.
"""
import os
import pytest
import httpx

BLURRING_URL = os.getenv("PLATE_BLURRING_URL", "http://localhost:8001")


@pytest.fixture(scope="module")
def client():
    try:
        httpx.get(f"{BLURRING_URL}/health", timeout=3)
    except Exception:
        pytest.skip("plate-blurring service not reachable")
    return httpx.Client(base_url=BLURRING_URL, timeout=10)


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_returns_ok_status(client):
    resp = client.get("/health")
    body = resp.json()
    assert body["status"] == "ok"


def test_health_model_loaded_is_true(client):
    resp = client.get("/health")
    body = resp.json()
    assert body["model_loaded"] is True
