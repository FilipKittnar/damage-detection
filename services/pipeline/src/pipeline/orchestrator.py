import logging
import tempfile
from pathlib import Path

import cv2

from pipeline.stages.blur_stage import BlurStage, BlurServiceUnavailableError
from pipeline.stages.damage_stage import DamageStage
from pipeline.stages.frame_extractor import extract_frames
from pipeline.stages.output_stage import OutputStage
from pipeline.storage.dynamo_client import DynamoClient
from pipeline.storage.event_publisher import EventPublisher
from pipeline.storage.s3_client import S3Client

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        dynamo_client: DynamoClient,
        s3_client: S3Client,
        event_publisher: EventPublisher,
        damage_stage: DamageStage,
        blur_stage: BlurStage,
        output_stage: OutputStage,
        bucket: str,
        frame_extraction_fps: float,
    ):
        self._dynamo = dynamo_client
        self._s3 = s3_client
        self._publisher = event_publisher
        self._damage = damage_stage
        self._blur = blur_stage
        self._output = output_stage
        self._bucket = bucket
        self._fps = frame_extraction_fps

    def process_job(self, bucket: str, key: str, job_id: str) -> None:
        existing = self._dynamo.get_job(job_id)
        if existing and existing.get("status") == "completed":
            logger.info("job_already_completed_skipping", extra={"job_id": job_id})
            return

        output_path = f"output/{job_id}"
        self._dynamo.create_job(job_id, key, output_path)
        self._publisher.publish("JobReceived", job_id, {"input_path": key})

        self._dynamo.update_job_status(job_id, "pending", "processing")
        self._publisher.publish("FrameExtractionStarted", job_id, {})

        video_path: Path | None = None
        try:
            video_path = self._s3.download_video(bucket, key)
            frame_count = 0
            damage_frame_count = 0
            blurred_frame_count = 0

            import cv2 as _cv2
            cap_check = _cv2.VideoCapture(str(video_path))
            if not cap_check.isOpened():
                cap_check.release()
                raise ValueError(f"Cannot open video file: {video_path}")
            cap_check.release()

            for frame_data in extract_frames(video_path, fps=self._fps):
                encoded, jpeg_bytes = cv2.imencode(".jpg", frame_data.bgr_array)
                if not encoded:
                    logger.warning("frame_encode_failed", extra={"job_id": job_id, "frame": frame_data.frame_index})
                    continue

                try:
                    annotated = self._damage.process(frame_data.bgr_array)
                except Exception as exc:
                    raise RuntimeError(f"Model inference failed on frame {frame_data.frame_index}: {exc}") from exc

                if annotated.detections:
                    damage_frame_count += 1

                _, annotated_jpeg = cv2.imencode(".jpg", annotated.annotated_frame)
                blurred_jpeg = self._blur.process(
                    annotated_jpeg.tobytes(), job_id=job_id, frame_index=frame_data.frame_index
                )
                blurred_frame_count += 1

                self._output.process(blurred_jpeg, job_id=job_id, frame_index=frame_data.frame_index)
                frame_count += 1

            if frame_count == 0:
                raise ValueError("Video contained zero extractable frames")

            self._dynamo.update_job_counters(job_id, frame_count, damage_frame_count, blurred_frame_count)
            self._dynamo.update_job_status(job_id, "processing", "completed")
            self._publisher.publish("JobCompleted", job_id, {
                "frame_count": frame_count,
                "damage_frame_count": damage_frame_count,
                "blurred_frame_count": blurred_frame_count,
            })
            logger.info("job_completed", extra={"job_id": job_id, "frames": frame_count})

        except BlurServiceUnavailableError as exc:
            self._fail_job(job_id, str(exc))
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
            if video_path and video_path.exists():
                video_path.unlink(missing_ok=True)

    def recover_stuck_jobs(self) -> None:
        error_msg = "Service restarted mid-job; re-trigger via SQS replay"
        for status in ("processing", "pending"):
            stuck = self._dynamo.scan_jobs_by_status(status)
            for job in stuck:
                job_id = job["job_id"]
                try:
                    self._dynamo.update_job_status(job_id, status, "failed", error=error_msg)
                    logger.info("recovered_stuck_job", extra={"job_id": job_id, "was_status": status})
                except Exception as exc:
                    logger.warning("recover_failed", extra={"job_id": job_id, "error": str(exc)})

    def _fail_job(self, job_id: str, error: str) -> None:
        try:
            job = self._dynamo.get_job(job_id)
            current_status = job["status"] if job else "processing"
            self._dynamo.update_job_status(job_id, current_status, "failed", error=error)
        except Exception as exc:
            logger.error("fail_job_update_failed", extra={"job_id": job_id, "error": str(exc)})
        self._publisher.publish("JobFailed", job_id, {"error": error})
        logger.error("job_failed", extra={"job_id": job_id, "error": error})
