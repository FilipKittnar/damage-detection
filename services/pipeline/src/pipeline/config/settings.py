import logging
import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        obj.update(record.__dict__.get("extra", {}))
        for key in ("msg", "args", "exc_info", "exc_text", "stack_info"):
            obj.pop(key, None)
        return json.dumps(obj, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    AWS_ENDPOINT_URL: str | None = None
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"

    S3_BUCKET: str = "damage-detection-local"
    SQS_INPUT_QUEUE_URL: str = "http://localhost:4566/000000000000/damage-detection-input"
    SQS_EVENTS_QUEUE_URL: str = "http://localhost:4566/000000000000/damage-detection-events"
    DYNAMODB_TABLE: str = "damage-detection-jobs"

    PLATE_BLURRING_URL: str = "http://plate-blurring:8001"
    FRAME_EXTRACTION_FPS: float = 1.0
    DAMAGE_MODEL_PATH: str = "models/damage_model.pt"
    DAMAGE_CONFIDENCE: float = 0.45


settings = Settings()
