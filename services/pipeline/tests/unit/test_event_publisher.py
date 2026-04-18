import json
import pytest
import boto3
from moto import mock_aws

from pipeline.storage.event_publisher import EventPublisher


BUCKET = "damage-detection-local"
QUEUE_NAME = "damage-detection-events"
REGION = "us-east-1"


@pytest.fixture
def publisher():
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
        sqs = boto3.client("sqs", region_name=REGION)
        queue_url = sqs.create_queue(QueueName=QUEUE_NAME)["QueueUrl"]
        yield EventPublisher(
            bucket=BUCKET,
            queue_url=queue_url,
            region=REGION,
            endpoint_url=None,
        )


def test_publish_sends_json_to_sqs(publisher):
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
        sqs = boto3.client("sqs", region_name=REGION)
        queue_url = sqs.create_queue(QueueName=QUEUE_NAME)["QueueUrl"]
        pub = EventPublisher(bucket=BUCKET, queue_url=queue_url, region=REGION, endpoint_url=None)
        pub.publish("JobCompleted", "fleet/job1/clip.mp4", {"frame_count": 10})
        msgs = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)["Messages"]
        assert len(msgs) == 1
        body = json.loads(msgs[0]["Body"])
        assert body["event_type"] == "JobCompleted"
        assert body["job_id"] == "fleet/job1/clip.mp4"
        assert "timestamp" in body
        assert body["payload"]["frame_count"] == 10


def test_publish_writes_json_to_s3(publisher):
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
        sqs = boto3.client("sqs", region_name=REGION)
        queue_url = sqs.create_queue(QueueName=QUEUE_NAME)["QueueUrl"]
        pub = EventPublisher(bucket=BUCKET, queue_url=queue_url, region=REGION, endpoint_url=None)
        pub.publish("JobFailed", "fleet/job2/clip.mp4", {"error": "oops"})
        s3 = boto3.client("s3", region_name=REGION)
        objs = s3.list_objects_v2(Bucket=BUCKET, Prefix="events/fleet/job2/clip.mp4/JobFailed-")
        assert objs.get("KeyCount", 0) == 1
