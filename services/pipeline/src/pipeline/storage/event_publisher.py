import json
import logging
from datetime import datetime, timezone

import boto3

from pipeline.storage.s3_client import S3Client

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, bucket: str, queue_url: str, region: str, endpoint_url: str | None):
        kwargs: dict = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._sqs = boto3.client("sqs", **kwargs)
        self._s3_client = S3Client(bucket=bucket, region=region, endpoint_url=endpoint_url)
        self._bucket = bucket
        self._queue_url = queue_url

    def publish(self, event_type: str, job_id: str, payload_dict: dict) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        message = {
            "event_type": event_type,
            "job_id": job_id,
            "timestamp": timestamp,
            "payload": payload_dict,
        }
        body = json.dumps(message, default=str)
        self._sqs.send_message(QueueUrl=self._queue_url, MessageBody=body)
        self._s3_client.write_event_json(self._bucket, job_id, event_type, message)
        logger.info("published_event", extra={"event_type": event_type, "job_id": job_id})
