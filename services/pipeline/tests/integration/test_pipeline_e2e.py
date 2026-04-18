"""
End-to-end integration test for the pipeline.
Requires Localstack + plate-blurring service running (via docker compose).
Skip automatically if services are not available.
"""
import os
import pytest
import boto3
import cv2
import numpy as np
import tempfile
from pathlib import Path

LOCALSTACK_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
PLATE_BLURRING_URL = os.getenv("PLATE_BLURRING_URL", "http://localhost:8001")
REGION = "us-east-1"
BUCKET = "damage-detection-local"
TABLE = "damage-detection-jobs"


def _localstack_available() -> bool:
    try:
        import httpx
        r = httpx.get(f"{LOCALSTACK_URL}/_localstack/health", timeout=3)
        return r.status_code < 400
    except Exception:
        return False


def _blurring_available() -> bool:
    try:
        import httpx
        r = httpx.get(f"{PLATE_BLURRING_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_localstack_available() and _blurring_available()),
    reason="Requires Localstack and plate-blurring service running",
)


def _make_test_video(path: Path) -> None:
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 1, (320, 240))
    for _ in range(3):
        out.write(np.zeros((240, 320, 3), dtype=np.uint8))
    out.release()


@pytest.fixture
def e2e_setup():
    s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_URL)
    dynamo = boto3.resource("dynamodb", region_name=REGION, endpoint_url=LOCALSTACK_URL)
    table = dynamo.Table(TABLE)
    return s3, table


def test_pipeline_processes_video_end_to_end(e2e_setup):
    from unittest.mock import MagicMock
    from pipeline.models.interfaces import BoundingBox
    from pipeline.stages.blur_stage import BlurStage
    from pipeline.stages.damage_stage import DamageStage
    from pipeline.stages.output_stage import OutputStage
    from pipeline.storage.dynamo_client import DynamoClient
    from pipeline.storage.event_publisher import EventPublisher
    from pipeline.storage.s3_client import S3Client
    from pipeline.orchestrator import Orchestrator

    s3_client, table = e2e_setup
    job_id = "integration-test/clip.mp4"
    key = f"input/{job_id}"

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        video_path = Path(f.name)
    _make_test_video(video_path)
    s3_client.upload_file(str(video_path), BUCKET, key)
    video_path.unlink()

    mock_detector = MagicMock()
    mock_detector.detect.return_value = []

    dynamo = DynamoClient(TABLE, REGION, LOCALSTACK_URL)
    s3 = S3Client(BUCKET, REGION, LOCALSTACK_URL)
    publisher = EventPublisher(
        BUCKET,
        f"{LOCALSTACK_URL}/000000000000/damage-detection-events",
        REGION,
        LOCALSTACK_URL,
    )
    damage_stage = DamageStage(detector=mock_detector)
    blur_stage = BlurStage(blurring_url=PLATE_BLURRING_URL)
    output_stage = OutputStage(s3_client=s3, bucket=BUCKET)

    orchestrator = Orchestrator(
        dynamo_client=dynamo, s3_client=s3, event_publisher=publisher,
        damage_stage=damage_stage, blur_stage=blur_stage,
        output_stage=output_stage, bucket=BUCKET, frame_extraction_fps=1.0,
    )
    orchestrator.process_job(BUCKET, key, job_id)

    job = dynamo.get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert int(job["frame_count"]) > 0

    resp = s3_client.list_objects_v2(Bucket=BUCKET, Prefix=f"output/{job_id}/")
    assert resp.get("KeyCount", 0) > 0, "Output frames should exist in S3"

    resp = s3_client.list_objects_v2(Bucket=BUCKET, Prefix=f"events/{job_id}/")
    assert resp.get("KeyCount", 0) > 0, "Event JSONs should exist in S3"
