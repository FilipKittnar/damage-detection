# Technologies

## Language & runtime

- **Python 3.11+** — both services
- **Docker 24+** and **Docker Compose v2** — orchestration

## Pipeline service (`services/pipeline`)

- **ultralytics** (YOLOv8) — damage detection inference
- **opencv-python** — video frame extraction, image annotation
- **boto3** — S3, SQS, DynamoDB clients
- **pydantic-settings** — environment-based config
- **httpx** — HTTP client for the plate-blurring service
- **pytest**, **pytest-asyncio**, **moto** (dev) — tests with mocked AWS

## Plate-blurring service (`services/plate-blurring`)

- **ultralytics** (YOLOv8) — licence-plate detection
- **opencv-python** — Gaussian blur
- **fastapi**, **uvicorn** — HTTP API
- **boto3**, **pydantic-settings**, **httpx**
- **pytest**, **pytest-asyncio** (dev)

## Infrastructure (local)

- **LocalStack 3** — emulates S3, SQS, DynamoDB on `http://localhost:4566`
- **AWS CLI v2** — manual interaction with LocalStack

Exact versions live in each service's `pyproject.toml`.
