# Research: End-to-End MVP Detection Pipeline

**Branch**: `001-mvp-detection-pipeline` | **Date**: 2026-04-18

---

## 1. Damage Detection Model

**Decision**: YOLOv8 (Ultralytics) with a community fine-tuned checkpoint for vehicle damage detection.

**Rationale**: Base YOLOv8 weights do not include a vehicle damage class. Fine-tuned community checkpoints (e.g., `nezahatkorkmaz/car-damage-level-detection-yolov8` on Hugging Face, or Roboflow Universe "Car Damage Detection" datasets) provide a ready-to-use starting point. YOLOv8 has a clear fine-tuning path for Renault-specific data (future spec), is fast enough for frame-by-frame processing, and exports cleanly to ONNX for deployment independence.

**Confidence threshold**: 0.45 (balances recall and precision; tune post-POC).

**Inference API**:
```python
from ultralytics import YOLO
model = YOLO("path/to/damage_model.pt")
results = model(frame_rgb)          # numpy array HWC uint8
boxes = results[0].boxes.xyxy.cpu().numpy()   # [[x1,y1,x2,y2], ...]
confs = results[0].boxes.conf.cpu().numpy()
```

**ONNX export** (deployment independence):
```bash
yolo export model=damage_model.pt format=onnx opset=12
```

**Alternatives considered**:
- Base YOLOv8n on COCO — rejected: no damage class, would require training from scratch.
- Grounding DINO / SAM — rejected: heavier, slower, more complex for a POC.
- HuggingFace DETR — rejected: less mature fine-tuning ecosystem vs. Ultralytics.

---

## 2. Licence Plate Detection Model

**Decision**: Specialized YOLOv8 model fine-tuned on licence plates (e.g., Roboflow Universe "YOLOv8 Number Plate Detection", ~5750 images).

**Rationale**: Generic YOLOv8 weights have no licence plate class. Dedicated LP detection models from Roboflow Universe provide multi-region support out of the box, which matters for a Renault Group deployment (EU plates, potentially other regions).

**Confidence threshold**: 0.45.

**Blurring**: After detecting plate bounding boxes, apply Gaussian blur to the region via OpenCV (`cv2.GaussianBlur`). Blur kernel size of (51, 51) provides sufficient obfuscation.

**Alternatives considered**:
- EasyOCR for plate localisation — rejected: OCR-focused, overkill for detection-only use case.
- LPRNet — rejected: recognition-focused, not pure detection.

---

## 3. Frame Extraction

**Decision**: OpenCV (`cv2`) with frame-index-based extraction (`frame_index % frame_skip == 0`).

**Rationale**: Frame index math is deterministic, fast, and avoids CAP_PROP_POS_MSEC seek overhead on large videos. Source FPS is read from the video header; `frame_skip = floor(source_fps / target_fps)`.

**Memory strategy**: Stream frames one at a time — never accumulate all frames in memory. Process and dispatch each frame immediately; use `gc.collect()` periodically for long videos.

**BGR → JPEG bytes**:
```python
# For downstream model + S3 upload
ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
jpeg_bytes = buf.tobytes()

# For PIL (model inference)
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
```

**Alternatives considered**:
- `CAP_PROP_POS_MSEC` time-based extraction — viable alternative; chosen frame-index math instead for simplicity and determinism.
- PyAV (FFmpeg bindings) — rejected: heavier dependency, overkill for POC.

---

## 4. S3 → SQS Event Notification

**Decision**: S3 direct notification to SQS standard queue (no SNS). Parse `Records[0].s3.bucket.name` and `Records[0].s3.object.key` (always `unquote_plus` the key).

**S3 event message structure**:
```json
{
  "Records": [{
    "eventName": "ObjectCreated:Put",
    "s3": {
      "bucket": { "name": "my-bucket" },
      "object": { "key": "input/fleet/vehicle-42/clip.mp4", "size": 104857600 }
    }
  }]
}
```

**Gotchas**:
- S3 keys are URL-encoded: always `from urllib.parse import unquote_plus` before use.
- S3 sends a `{"Event": "s3:TestEvent", ...}` message on initial configuration — filter and discard it.
- Multiple Records per message is theoretically possible; always iterate `Records`.
- Localstack: standard queues only (FIFO silently fails); SQS queue must have an IAM policy granting `sqs:SendMessage` to `s3.amazonaws.com`.

**Localstack SQS ARN format**: `arn:aws:sqs:us-east-1:000000000000:<queue-name>`

---

## 5. SQS Consumer Pattern

**Decision**: Long polling consumer with visibility timeout heartbeat for long-running jobs.

**Pattern**:
```python
response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=1,
    WaitTimeSeconds=20,          # long polling
    VisibilityTimeout=300,       # 5 min initial; extended by heartbeat
)
```

**Heartbeat**: A background thread calls `change_message_visibility` every 60 seconds to extend the visibility timeout while a job is processing. This prevents the message from re-appearing in the queue for a job that is still running.

**Delete only on success**: If processing fails, the message is left in the queue and re-delivered after the visibility timeout expires (natural retry). FR-012 (startup crash recovery) prevents orphaned `processing` jobs from blocking subsequent retries.

**Alternatives considered**:
- EventBridge Pipe — rejected: additional infra complexity, not supported cleanly in Localstack for POC.
- SNS → SQS — rejected by user (clarification Q1); S3 → SQS direct chosen.

---

## 6. DynamoDB Job Table

**Decision**: Single table `damage-detection-jobs`, partition key `job_id` (String), no sort key needed.

**Atomic status transitions** via `ConditionExpression`:
```python
table.update_item(
    Key={'job_id': job_id},
    UpdateExpression='SET #s = :new, updated_at = :ts',
    ConditionExpression=Attr('#s').eq(expected_current),
    ExpressionAttributeNames={'#s': 'status'},   # 'status' is a DynamoDB reserved word
    ExpressionAttributeValues={':new': new_status, ':ts': now},
)
```

**Important**: `status` is a DynamoDB reserved word — always alias it as `#s` or `#status` in expressions.

**Alternatives considered**:
- Sort key on `created_at` for range queries — deferred: not needed for POC single-job queries.
- PostgreSQL — rejected: constitution specifies DynamoDB; unnecessary for POC scope.

---

## 7. Licence Plate Blurring Service (FastAPI)

**Decision**: FastAPI HTTP microservice, `POST /v1/blur` accepts `multipart/form-data` image upload, returns JSON with base64-encoded blurred image + detection metadata.

**Rationale**: JSON response (base64 + metadata) is easier to test, log, and assert against in integration tests vs. raw binary stream. Overhead of base64 is acceptable for POC frame sizes.

**Alternatives considered**:
- Direct Python function call (same process) — rejected: constitution requires independently deployable service.
- Binary image response (`image/jpeg`) — viable but harder to test and lacks metadata; deferred to future optimisation.

---

## 8. Local Development

**Decision**: Docker Compose + Localstack v3. One `docker-compose.yml` for both services + Localstack. An `infra/localstack/init-aws.sh` script creates the S3 bucket and both SQS queues on startup.

**Localstack configuration**:
- Services: `s3,sqs,dynamodb`
- S3 bucket: `damage-detection-local`
- SQS queues: `damage-detection-input`, `damage-detection-events`
- DynamoDB table: `damage-detection-jobs`

**Known Localstack quirks**:
- FIFO queues do not work with S3 notifications — use standard queues.
- Queue IAM policy (`sqs:SendMessage` for `s3.amazonaws.com`) is required even in Localstack.
- No `s3:TestEvent` is sent by Localstack (unlike real AWS).
