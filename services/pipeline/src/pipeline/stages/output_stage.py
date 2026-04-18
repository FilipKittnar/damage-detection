import logging

from pipeline.storage.s3_client import S3Client

logger = logging.getLogger(__name__)


class OutputStage:
    def __init__(self, s3_client: S3Client, bucket: str):
        self._s3 = s3_client
        self._bucket = bucket

    def process(self, jpeg_bytes: bytes, job_id: str, frame_index: int) -> None:
        self._s3.upload_frame(self._bucket, job_id, frame_index, jpeg_bytes)
        logger.debug("output_stage_done", extra={"job_id": job_id, "frame_index": frame_index})
