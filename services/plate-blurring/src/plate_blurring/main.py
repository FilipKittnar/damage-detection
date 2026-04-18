import uvicorn

from plate_blurring.api.app import configure_logging, create_production_app
from plate_blurring.config.settings import settings

configure_logging()

app = create_production_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
