import json
import logging
import threading
import time
from typing import Callable
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger(__name__)

_VISIBILITY_HEARTBEAT_SECONDS = 60
_VISIBILITY_EXTENSION_SECONDS = 180


class SqsConsumer:
    def __init__(
        self,
        queue_url: str,
        handler_fn: Callable[[str, str, str], None],
        region: str,
        endpoint_url: str | None,
    ):
        kwargs: dict = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._sqs = boto3.client("sqs", **kwargs)
        self._queue_url = queue_url
        self._handler = handler_fn

    def consume(self) -> None:
        logger.info("sqs_consumer_started", extra={"queue": self._queue_url})
        while True:
            try:
                self._poll_once()
            except Exception as exc:
                logger.error("consumer_poll_error", extra={"error": str(exc)})
                time.sleep(5)

    def _poll_once(self) -> None:
        resp = self._sqs.receive_message(
            QueueUrl=self._queue_url,
            WaitTimeSeconds=20,
            MaxNumberOfMessages=1,
            AttributeNames=["All"],
        )
        messages = resp.get("Messages", [])
        if not messages:
            return

        message = messages[0]
        receipt_handle = message["ReceiptHandle"]
        body = json.loads(message["Body"])

        if body.get("Event") == "s3:TestEvent":
            logger.debug("filtered_s3_test_event")
            self._sqs.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
            return

        records = body.get("Records", [])
        if not records:
            self._sqs.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
            return

        record = records[0]
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        job_id = key.removeprefix("input/")

        stop_event = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat,
            args=(receipt_handle, stop_event),
            daemon=True,
        )
        heartbeat.start()

        try:
            self._handler(bucket, key, job_id)
            self._sqs.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
            logger.info("message_processed", extra={"job_id": job_id})
        except Exception as exc:
            logger.error("message_handler_failed", extra={"job_id": job_id, "error": str(exc)})
        finally:
            stop_event.set()
            heartbeat.join(timeout=2)

    def _heartbeat(self, receipt_handle: str, stop: threading.Event) -> None:
        while not stop.wait(timeout=_VISIBILITY_HEARTBEAT_SECONDS):
            try:
                self._sqs.change_message_visibility(
                    QueueUrl=self._queue_url,
                    ReceiptHandle=receipt_handle,
                    VisibilityTimeout=_VISIBILITY_EXTENSION_SECONDS,
                )
                logger.debug("visibility_extended")
            except Exception as exc:
                logger.warning("heartbeat_failed", extra={"error": str(exc)})
                break
