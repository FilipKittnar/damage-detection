import pytest
import boto3
from moto import mock_aws

from pipeline.storage.dynamo_client import DynamoClient


TABLE = "damage-detection-jobs"
REGION = "us-east-1"


@pytest.fixture
def dynamo_client():
    with mock_aws():
        boto3.client("dynamodb", region_name=REGION).create_table(
            TableName=TABLE,
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield DynamoClient(table_name=TABLE, region=REGION, endpoint_url=None)


def test_create_job_creates_record_with_pending_status(dynamo_client):
    dynamo_client.create_job("job1", "input/job1/clip.mp4", "output/job1/clip.mp4")
    item = dynamo_client.get_job("job1")
    assert item is not None
    assert item["job_id"] == "job1"
    assert item["status"] == "pending"
    assert item["input_path"] == "input/job1/clip.mp4"
    assert item["output_path"] == "output/job1/clip.mp4"


def test_get_job_returns_none_for_missing(dynamo_client):
    assert dynamo_client.get_job("nonexistent") is None


def test_update_job_status_transitions_atomically(dynamo_client):
    dynamo_client.create_job("job2", "input/job2/v.mp4", "output/job2/v.mp4")
    dynamo_client.update_job_status("job2", "pending", "processing")
    item = dynamo_client.get_job("job2")
    assert item["status"] == "processing"


def test_update_job_status_raises_on_wrong_current_status(dynamo_client):
    from botocore.exceptions import ClientError
    dynamo_client.create_job("job3", "input/job3/v.mp4", "output/job3/v.mp4")
    with pytest.raises(ClientError, match="ConditionalCheckFailedException"):
        dynamo_client.update_job_status("job3", "processing", "completed")


def test_update_job_counters(dynamo_client):
    dynamo_client.create_job("job4", "input/job4/v.mp4", "output/job4/v.mp4")
    dynamo_client.update_job_counters("job4", frame_count=60, damage_frame_count=5, blurred_frame_count=3)
    item = dynamo_client.get_job("job4")
    assert item["frame_count"] == 60
    assert item["damage_frame_count"] == 5
    assert item["blurred_frame_count"] == 3
