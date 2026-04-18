#!/usr/bin/env bash
# Localstack initialisation script — runs automatically on container startup.
# Creates all AWS resources needed by the pipeline.
set -euo pipefail

REGION="us-east-1"
ACCOUNT="000000000000"
BUCKET="damage-detection-local"
INPUT_QUEUE="damage-detection-input"
EVENTS_QUEUE="damage-detection-events"
TABLE="damage-detection-jobs"
ENDPOINT="http://localhost:4566"

AWS="aws --endpoint-url=${ENDPOINT} --region=${REGION} --output=json"

echo "--- Creating S3 bucket: ${BUCKET} ---"
$AWS s3api create-bucket --bucket "${BUCKET}" || true

echo "--- Creating SQS queue: ${EVENTS_QUEUE} ---"
$AWS sqs create-queue --queue-name "${EVENTS_QUEUE}" || true

echo "--- Creating SQS queue: ${INPUT_QUEUE} ---"
INPUT_QUEUE_URL=$($AWS sqs create-queue --queue-name "${INPUT_QUEUE}" \
  --query 'QueueUrl' --output text)
INPUT_QUEUE_ARN="arn:aws:sqs:${REGION}:${ACCOUNT}:${INPUT_QUEUE}"

echo "--- Setting SQS queue policy to allow S3 to send messages ---"
POLICY=$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": "sqs:SendMessage",
      "Resource": "${INPUT_QUEUE_ARN}"
    }
  ]
}
POLICY
)
$AWS sqs set-queue-attributes \
  --queue-url "${INPUT_QUEUE_URL}" \
  --attributes "Policy=$(echo ${POLICY} | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"

echo "--- Configuring S3 bucket notification -> SQS ---"
NOTIFICATION=$(cat <<NOTIF
{
  "QueueConfigurations": [
    {
      "QueueArn": "${INPUT_QUEUE_ARN}",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [{"Name": "prefix", "Value": "input/"}]
        }
      }
    }
  ]
}
NOTIF
)
$AWS s3api put-bucket-notification-configuration \
  --bucket "${BUCKET}" \
  --notification-configuration "${NOTIFICATION}"

echo "--- Creating DynamoDB table: ${TABLE} ---"
$AWS dynamodb create-table \
  --table-name "${TABLE}" \
  --attribute-definitions AttributeName=job_id,AttributeType=S \
  --key-schema AttributeName=job_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST || true

echo "--- Localstack init complete ---"
