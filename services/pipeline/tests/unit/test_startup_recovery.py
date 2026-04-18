import pytest
import boto3
from moto import mock_aws
from unittest.mock import MagicMock

from pipeline.storage.dynamo_client import DynamoClient

TABLE = "damage-detection-jobs"
REGION = "us-east-1"


@pytest.fixture
def dynamo_and_orchestrator():
    with mock_aws():
        boto3.client("dynamodb", region_name=REGION).create_table(
            TableName=TABLE,
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamo = DynamoClient(TABLE, REGION, None)
        dynamo.create_job("job-proc-1", "input/j1/v.mp4", "output/j1/v.mp4")
        dynamo.update_job_status("job-proc-1", "pending", "processing")
        dynamo.create_job("job-proc-2", "input/j2/v.mp4", "output/j2/v.mp4")
        dynamo.update_job_status("job-proc-2", "pending", "processing")
        dynamo.create_job("job-done", "input/j3/v.mp4", "output/j3/v.mp4")
        dynamo.update_job_status("job-done", "pending", "processing")
        dynamo.update_job_status("job-done", "processing", "completed")

        from pipeline.orchestrator import Orchestrator
        mock_pub = MagicMock()
        mock_s3 = MagicMock()
        orch = Orchestrator(
            dynamo_client=dynamo,
            s3_client=mock_s3,
            event_publisher=mock_pub,
            damage_stage=MagicMock(),
            blur_stage=MagicMock(),
            output_stage=MagicMock(),
            bucket="test-bucket",
            frame_extraction_fps=1.0,
        )
        yield dynamo, orch


def test_recover_marks_processing_jobs_as_failed(dynamo_and_orchestrator):
    dynamo, orch = dynamo_and_orchestrator
    orch.recover_stuck_jobs()
    j1 = dynamo.get_job("job-proc-1")
    j2 = dynamo.get_job("job-proc-2")
    assert j1["status"] == "failed"
    assert j2["status"] == "failed"
    assert "error" in j1
    assert "error" in j2


def test_recover_leaves_completed_jobs_unchanged(dynamo_and_orchestrator):
    dynamo, orch = dynamo_and_orchestrator
    orch.recover_stuck_jobs()
    done = dynamo.get_job("job-done")
    assert done["status"] == "completed"
