# Quickstart: End-to-End MVP Detection Pipeline

**Branch**: `001-mvp-detection-pipeline` | **Date**: 2026-04-18

---

## Prerequisites

- Docker 24+ and Docker Compose v2
- Python 3.11+ (for running tests outside containers)
- `aws` CLI v2 (for manual S3/SQS interaction with Localstack)
- `git`

No live AWS credentials are needed.

---

## 1. Start the Local Environment

```bash
# From the repository root
docker compose up --build
```

This starts:
- **Localstack** (S3, SQS, DynamoDB) on `http://localhost:4566`
- **Plate Blurring Service** on `http://localhost:8001`
- **Pipeline Service** (SQS consumer, starts listening immediately)

The `infra/localstack/init-aws.sh` script runs automatically on Localstack startup and creates:
- S3 bucket: `damage-detection-local`
- SQS queue (input): `damage-detection-input`
- SQS queue (events): `damage-detection-events`
- DynamoDB table: `damage-detection-jobs`
- S3 event notification: `damage-detection-local` → `damage-detection-input` on `s3:ObjectCreated:*` for prefix `input/`

Wait until you see `Localstack ready` and `Pipeline Service: listening for jobs` in the logs.

---

## 2. Verify Services are Healthy

```bash
# Blurring service
curl http://localhost:8001/health
# Expected: {"status": "ok", "model_loaded": true}

# Localstack
aws --endpoint-url=http://localhost:4566 sqs list-queues
# Expected: QueueUrls containing damage-detection-input and damage-detection-events
```

---

## 3. Submit a Test Video (Simulate External System)

Upload a video to the S3 input path. This simulates what the external system does.

```bash
aws --endpoint-url=http://localhost:4566 \
  s3 cp /path/to/your/test-video.mp4 \
  s3://damage-detection-local/input/test-job/clip.mp4
```

The S3 event fires automatically. The Pipeline Service picks it up from the SQS queue within seconds and begins processing.

---

## 4. Monitor Pipeline Progress

**Watch service logs**:
```bash
docker compose logs -f pipeline
```

**Check job status in DynamoDB**:
```bash
aws --endpoint-url=http://localhost:4566 dynamodb get-item \
  --table-name damage-detection-jobs \
  --key '{"job_id": {"S": "test-job/clip.mp4"}}'
```

**Expected status progression**: `pending` → `processing` → `completed`

---

## 5. Inspect Output

**Annotated frames** (S3 output bucket):
```bash
aws --endpoint-url=http://localhost:4566 \
  s3 ls s3://damage-detection-local/output/test-job/clip.mp4/

# Download all output frames
aws --endpoint-url=http://localhost:4566 \
  s3 sync s3://damage-detection-local/output/test-job/clip.mp4/ ./output-frames/
```

**Domain event JSON dump** (POC verification):
```bash
aws --endpoint-url=http://localhost:4566 \
  s3 ls s3://damage-detection-local/events/test-job/clip.mp4/

# Download and inspect a specific event
aws --endpoint-url=http://localhost:4566 \
  s3 cp s3://damage-detection-local/events/test-job/clip.mp4/JobCompleted-*.json -
```

**Output events queue** (what the downstream module would receive):
```bash
aws --endpoint-url=http://localhost:4566 sqs receive-message \
  --queue-url http://localhost:4566/000000000000/damage-detection-events \
  --max-number-of-messages 10
```

---

## 6. Run Tests

```bash
# Unit tests (no Docker required)
cd services/pipeline
python -m pytest tests/unit/ -v

cd services/plate-blurring
python -m pytest tests/unit/ -v

# Integration tests (requires Docker Compose running)
cd services/pipeline
python -m pytest tests/integration/ -v

# Contract tests (requires Docker Compose running)
cd services/pipeline
python -m pytest tests/contract/ -v
```

---

## 7. Tear Down

```bash
docker compose down -v
```

The `-v` flag removes Localstack data volumes, giving a clean slate for the next run.

---

## Environment Variables

The Pipeline Service is configured via environment variables (set in `docker-compose.yml`; override with a `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_ENDPOINT_URL` | `http://localstack:4566` | Localstack endpoint (unset for real AWS) |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | `test` | Dummy value for Localstack |
| `AWS_SECRET_ACCESS_KEY` | `test` | Dummy value for Localstack |
| `S3_BUCKET` | `damage-detection-local` | S3 bucket name |
| `SQS_INPUT_QUEUE_URL` | `http://localstack:4566/000000000000/damage-detection-input` | Input SQS queue URL |
| `SQS_EVENTS_QUEUE_URL` | `http://localstack:4566/000000000000/damage-detection-events` | Output events SQS queue URL |
| `DYNAMODB_TABLE` | `damage-detection-jobs` | DynamoDB table name |
| `PLATE_BLURRING_URL` | `http://plate-blurring:8001` | Blurring service base URL |
| `FRAME_EXTRACTION_FPS` | `1.0` | Frames to extract per second of video |
| `DAMAGE_MODEL_PATH` | `models/damage_model.pt` | Path to YOLOv8 damage detection weights |
| `DAMAGE_CONFIDENCE` | `0.45` | Detection confidence threshold |

The Plate Blurring Service:

| Variable | Default | Description |
|----------|---------|-------------|
| `PLATE_MODEL_PATH` | `models/plate_model.pt` | Path to YOLOv8 licence plate model weights |
| `PLATE_CONFIDENCE` | `0.45` | Detection confidence threshold |
| `BLUR_KERNEL_SIZE` | `51` | Gaussian blur kernel size (odd number) |
| `PORT` | `8001` | FastAPI port |

---

## Troubleshooting

**Pipeline does not start processing after upload**:
- Check Localstack logs: `docker compose logs localstack`
- Verify S3 notification is configured: `aws --endpoint-url=http://localhost:4566 s3api get-bucket-notification-configuration --bucket damage-detection-local`
- Check the input SQS queue for messages: `aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes --queue-url ... --attribute-names All`

**Job stuck in `processing` after restart**:
- This is expected behaviour (FR-012). The job will be marked `failed` on Pipeline Service startup.
- Re-trigger by re-uploading the video file to S3.

**Blurring service reports model not loaded**:
- Check that `models/plate_model.pt` exists in the `services/plate-blurring/` directory.
- Model weights are not included in the repo; download instructions are in `services/plate-blurring/README.md`.
