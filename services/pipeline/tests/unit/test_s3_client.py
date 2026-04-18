import pytest
import boto3
from moto import mock_aws

from pipeline.storage.s3_client import S3Client


BUCKET = "damage-detection-local"
REGION = "us-east-1"


@pytest.fixture
def s3_client():
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
        yield S3Client(bucket=BUCKET, region=REGION, endpoint_url=None)


def test_upload_frame_puts_jpeg_at_correct_key(s3_client, tmp_path):
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal fake JPEG header
    s3_client.upload_frame(BUCKET, "fleet/job1/clip.mp4", 0, jpeg_bytes)
    s3 = boto3.client("s3", region_name=REGION)
    obj = s3.get_object(Bucket=BUCKET, Key="output/fleet/job1/clip.mp4/frame_0000.jpg")
    assert obj["Body"].read() == jpeg_bytes


def test_upload_frame_zero_pads_index(s3_client):
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 10
    s3_client.upload_frame(BUCKET, "job2/v.mp4", 42, jpeg_bytes)
    s3 = boto3.client("s3", region_name=REGION)
    obj = s3.get_object(Bucket=BUCKET, Key="output/job2/v.mp4/frame_0042.jpg")
    assert obj["Body"].read() == jpeg_bytes


def test_write_event_json_puts_json_at_correct_key(s3_client):
    s3_client.write_event_json(BUCKET, "job5/v.mp4", "JobCompleted", {"status": "completed"})
    s3 = boto3.client("s3", region_name=REGION)
    objs = s3.list_objects_v2(Bucket=BUCKET, Prefix="events/job5/v.mp4/JobCompleted-")
    keys = [o["Key"] for o in objs.get("Contents", [])]
    assert len(keys) == 1
    assert keys[0].startswith("events/job5/v.mp4/JobCompleted-")
    assert keys[0].endswith(".json")


def test_download_video_returns_path(s3_client, tmp_path):
    s3 = boto3.client("s3", region_name=REGION)
    s3.put_object(Bucket=BUCKET, Key="input/job6/clip.mp4", Body=b"fake-video")
    path = s3_client.download_video(BUCKET, "input/job6/clip.mp4")
    assert path.exists()
    assert path.read_bytes() == b"fake-video"
