# Local setup

## Prerequisites

- Docker 24+ and Docker Compose v2
- Python 3.11+ (only needed to run tests outside containers)
- AWS CLI v2 (to push test videos and inspect results)

No real AWS credentials required — LocalStack uses dummy values.

## Model weights

YOLOv8 weights are not checked in. Before the first run, place them at:

```text
models/pipeline/damage_model.pt
models/plate-blurring/plate_model.pt
```

These directories are mounted into the containers by [`docker-compose.yml`](../docker-compose.yml).

## Start the stack

From the repo root:

```bash
docker compose up --build
```

This starts LocalStack, the plate-blurring service, and the pipeline service. The [`infra/localstack/init-aws.sh`](../infra/localstack/init-aws.sh) script creates the S3 bucket, both SQS queues, the DynamoDB table, and the S3 → SQS notification for the `input/` prefix.

Wait for `Localstack ready` and the pipeline log line confirming it is listening for jobs.

## Verify the stack

```bash
curl http://localhost:8001/health
aws --endpoint-url=http://localhost:4566 sqs list-queues
```

## Submit a test video

```bash
aws --endpoint-url=http://localhost:4566 s3 cp ./test-video.mp4 \
  s3://damage-detection-local/input/test-job/clip.mp4
```

The pipeline picks up the SQS event within seconds and begins processing.

## Inspect results

```bash
# Job status
aws --endpoint-url=http://localhost:4566 dynamodb get-item \
  --table-name damage-detection-jobs \
  --key '{"job_id": {"S": "test-job/clip.mp4"}}'

# Annotated frames
aws --endpoint-url=http://localhost:4566 s3 ls \
  s3://damage-detection-local/output/test-job/clip.mp4/

# Domain events
aws --endpoint-url=http://localhost:4566 sqs receive-message \
  --queue-url http://localhost:4566/000000000000/damage-detection-events \
  --max-number-of-messages 10
```

## Tear down

```bash
docker compose down -v
```

The `-v` flag drops LocalStack's volume for a clean next run.
