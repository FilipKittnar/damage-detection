import logging
import sys

import httpx

from pipeline.config.settings import settings, configure_logging
from pipeline.consumer import SqsConsumer
from pipeline.orchestrator import Orchestrator
from pipeline.stages.blur_stage import BlurStage
from pipeline.stages.damage_stage import DamageStage
from pipeline.stages.output_stage import OutputStage
from pipeline.storage.dynamo_client import DynamoClient
from pipeline.storage.event_publisher import EventPublisher
from pipeline.storage.s3_client import S3Client

configure_logging()
logger = logging.getLogger(__name__)


def _check_blurring_service() -> None:
    try:
        resp = httpx.get(f"{settings.PLATE_BLURRING_URL}/health", timeout=10)
        if resp.status_code != 200:
            logger.error("plate_blurring_unhealthy", extra={"status": resp.status_code})
            sys.exit(1)
    except Exception as exc:
        logger.error("plate_blurring_unreachable", extra={"error": str(exc)})
        sys.exit(1)
    logger.info("plate_blurring_healthy")


def main() -> None:
    logger.info("pipeline_starting")

    dynamo = DynamoClient(
        table_name=settings.DYNAMODB_TABLE,
        region=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    )
    s3 = S3Client(
        bucket=settings.S3_BUCKET,
        region=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    )
    publisher = EventPublisher(
        bucket=settings.S3_BUCKET,
        queue_url=settings.SQS_EVENTS_QUEUE_URL,
        region=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    )

    from pipeline.models.yolov8.damage_detector import YoloV8DamageDetector
    detector = YoloV8DamageDetector(
        model_path=settings.DAMAGE_MODEL_PATH,
        confidence=settings.DAMAGE_CONFIDENCE,
    )

    damage_stage = DamageStage(detector=detector)
    blur_stage = BlurStage(blurring_url=settings.PLATE_BLURRING_URL)
    output_stage = OutputStage(s3_client=s3, bucket=settings.S3_BUCKET)

    orchestrator = Orchestrator(
        dynamo_client=dynamo,
        s3_client=s3,
        event_publisher=publisher,
        damage_stage=damage_stage,
        blur_stage=blur_stage,
        output_stage=output_stage,
        bucket=settings.S3_BUCKET,
        frame_extraction_fps=settings.FRAME_EXTRACTION_FPS,
    )

    orchestrator.recover_stuck_jobs()
    _check_blurring_service()

    consumer = SqsConsumer(
        queue_url=settings.SQS_INPUT_QUEUE_URL,
        handler_fn=orchestrator.process_job,
        region=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    )

    logger.info("pipeline_listening_for_jobs")
    consumer.consume()


if __name__ == "__main__":
    main()
