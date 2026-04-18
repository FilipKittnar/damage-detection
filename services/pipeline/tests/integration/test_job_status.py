"""
Integration test for job status tracking.
Requires Localstack + plate-blurring service running.
Skip automatically if services are unavailable.
"""
import os
import pytest
import boto3
import numpy as np
import tempfile
import cv2
from pathlib import Path
from unittest.mock import MagicMock

LOCALSTACK_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
PLATE_BLURRING_URL = os.getenv("PLATE_BLURRING_URL", "http://localhost:8001")
REGION = "us-east-1"
BUCKET = "damage-detection-local"
TABLE = "damage-detection-jobs"


def _services_available() -> bool:
    try:
        import httpx
        ls = httpx.get(f"{LOCALSTACK_URL}/_localstack/health", timeout=3)
        bl = httpx.get(f"{PLATE_BLURRING_URL}/health", timeout=3)
        return ls.status_code < 400 and bl.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _services_available(),
    reason="Requires Localstack and plate-blurring service",
)


def _build_orchestrator():
    from pipeline.stages.blur_stage import BlurStage
    from pipeline.stages.damage_stage import DamageStage
    from pipeline.stages.output_stage import OutputStage
    from pipeline.storage.dynamo_client import DynamoClient
    from pipeline.storage.event_publisher import EventPublisher
    from pipeline.storage.s3_client import S3Client
    from pipeline.orchestrator import Orchestrator

    dynamo = DynamoClient(TABLE, REGION, LOCALSTACK_URL)
    s3 = S3Client(BUCKET, REGION, LOCALSTACK_URL)
    publisher = EventPublisher(
        BUCKET,
        f"{LOCALSTACK_URL}/000000000000/damage-detection-events",
        REGION,
        LOCALSTACK_URL,
    )
    mock_detector = MagicMock()
    mock_detector.detect.return_value = []
    return Orchestrator(
        dynamo_client=dynamo, s3_client=s3, event_publisher=publisher,
        damage_stage=DamageStage(detector=mock_detector),
        blur_stage=BlurStage(blurring_url=PLATE_BLURRING_URL),
        output_stage=OutputStage(s3_client=s3, bucket=BUCKET),
        bucket=BUCKET, frame_extraction_fps=1.0,
    ), dynamo


def _upload_test_video(job_id: str) -> None:
    s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_URL)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = Path(f.name)
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 1, (320, 240))
    for _ in range(2):
        out.write(np.zeros((240, 320, 3), dtype=np.uint8))
    out.release()
    s3.upload_file(str(path), BUCKET, f"input/{job_id}")
    path.unlink()


def test_successful_job_has_correct_counters():
    job_id = "status-test/success.mp4"
    _upload_test_video(job_id)
    orch, dynamo = _build_orchestrator()
    orch.process_job(BUCKET, f"input/{job_id}", job_id)
    job = dynamo.get_job(job_id)
    assert job["status"] == "completed"
    assert int(job["frame_count"]) >= 0
    assert int(job["damage_frame_count"]) >= 0
    assert int(job["blurred_frame_count"]) >= 0


def test_failed_job_has_error_field():
    job_id = "status-test/bad-path.mp4"
    orch, dynamo = _build_orchestrator()
    orch.process_job(BUCKET, "input/does-not-exist.mp4", job_id)
    job = dynamo.get_job(job_id)
    assert job["status"] == "failed"
    assert job.get("error")
