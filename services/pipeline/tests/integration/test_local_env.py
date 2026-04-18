"""
Integration test: verifies the full local Docker Compose environment is healthy.
Requires `docker compose up` to be running.
Skips automatically if services are not available.
"""
import os
import pytest
import httpx

LOCALSTACK_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
PLATE_BLURRING_URL = os.getenv("PLATE_BLURRING_URL", "http://localhost:8001")
REGION = "us-east-1"
BUCKET = "damage-detection-local"
INPUT_QUEUE = "damage-detection-input"
EVENTS_QUEUE = "damage-detection-events"
TABLE = "damage-detection-jobs"


def _localstack_available() -> bool:
    try:
        r = httpx.get(f"{LOCALSTACK_URL}/_localstack/health", timeout=3)
        return r.status_code < 400
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _localstack_available(),
    reason="Requires docker compose up (Localstack not reachable)",
)


def test_localstack_responds():
    r = httpx.get(f"{LOCALSTACK_URL}/_localstack/health", timeout=5)
    assert r.status_code < 400


def test_s3_bucket_exists():
    import boto3
    s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_URL,
                      aws_access_key_id="test", aws_secret_access_key="test")
    buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    assert BUCKET in buckets


def test_sqs_queues_exist():
    import boto3
    sqs = boto3.client("sqs", region_name=REGION, endpoint_url=LOCALSTACK_URL,
                       aws_access_key_id="test", aws_secret_access_key="test")
    resp = sqs.list_queues()
    urls = resp.get("QueueUrls", [])
    names = [u.split("/")[-1] for u in urls]
    assert INPUT_QUEUE in names
    assert EVENTS_QUEUE in names


def test_dynamodb_table_exists():
    import boto3
    dynamo = boto3.client("dynamodb", region_name=REGION, endpoint_url=LOCALSTACK_URL,
                          aws_access_key_id="test", aws_secret_access_key="test")
    tables = dynamo.list_tables().get("TableNames", [])
    assert TABLE in tables


def test_plate_blurring_service_healthy():
    r = httpx.get(f"{PLATE_BLURRING_URL}/health", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
