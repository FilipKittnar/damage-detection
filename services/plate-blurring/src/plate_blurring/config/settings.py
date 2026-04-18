from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PLATE_MODEL_PATH: str = "models/plate_model.pt"
    PLATE_CONFIDENCE: float = 0.45
    BLUR_KERNEL_SIZE: int = 51
    PORT: int = 8001


settings = Settings()
