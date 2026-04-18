import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from plate_blurring.models.interfaces import PlateDetector

logger = logging.getLogger(__name__)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(obj, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def create_app(detector: PlateDetector | None = None) -> FastAPI:
    """Factory that accepts an injected detector (used in tests and production alike)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if detector is not None:
            app.state.detector = detector
        yield

    app = FastAPI(title="Plate Blurring Service", lifespan=lifespan)

    if detector is not None:
        app.state.detector = detector
    else:
        app.state.detector = None

    from plate_blurring.api.routes import router
    app.include_router(router)

    return app


def create_production_app() -> FastAPI:
    from plate_blurring.config.settings import settings
    from plate_blurring.models.yolov8.plate_detector import YoloV8PlateDetector

    try:
        detector = YoloV8PlateDetector(
            model_path=settings.PLATE_MODEL_PATH,
            confidence=settings.PLATE_CONFIDENCE,
            blur_kernel_size=settings.BLUR_KERNEL_SIZE,
        )
        logger.info("plate_model_loaded", extra={"path": settings.PLATE_MODEL_PATH})
    except Exception as exc:
        logger.error("plate_model_load_failed", extra={"error": str(exc)})
        detector = None

    return create_app(detector=detector)
