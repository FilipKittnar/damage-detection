import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)


class S3Client:
    def __init__(self, bucket: str, region: str, endpoint_url: str | None):
        kwargs: dict = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._s3 = boto3.client("s3", **kwargs)
        self._bucket = bucket

    def download_video(self, bucket: str, key: str) -> Path:
        suffix = Path(key).suffix or ".mp4"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        self._s3.download_fileobj(bucket, key, tmp)
        tmp.flush()
        tmp.close()
        logger.info("downloaded_video", extra={"key": key, "path": tmp.name})
        return Path(tmp.name)

    def upload_frame(self, bucket: str, job_id: str, frame_index: int, jpeg_bytes: bytes) -> None:
        key = f"output/{job_id}/frame_{frame_index:04d}.jpg"
        self._s3.put_object(Bucket=bucket, Key=key, Body=jpeg_bytes, ContentType="image/jpeg")
        logger.debug("uploaded_frame", extra={"key": key})

    def write_event_json(
        self,
        bucket: str,
        job_id: str,
        event_type: str,
        payload_dict: dict,
    ) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        key = f"events/{job_id}/{event_type}-{timestamp}.json"
        self._s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(payload_dict, default=str).encode(),
            ContentType="application/json",
        )
        logger.debug("wrote_event_json", extra={"key": key})
