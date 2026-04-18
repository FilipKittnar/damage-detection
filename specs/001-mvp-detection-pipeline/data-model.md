# Data Model: End-to-End MVP Detection Pipeline

**Branch**: `001-mvp-detection-pipeline` | **Date**: 2026-04-18

---

## Entities

### Job

Represents a single video processing request, created when an S3 event is first received.

| Attribute | Type | Notes |
|-----------|------|-------|
| `job_id` | String (PK) | S3 object key with `/input/` prefix stripped. E.g. `fleet/vehicle-42/clip.mp4`. URL-decoded. |
| `status` | String (Enum) | `pending` → `processing` → `completed` \| `failed` |
| `input_s3_path` | String | Full S3 URI: `s3://<bucket>/input/<job_id>` |
| `output_s3_path` | String | Full S3 URI: `s3://<bucket>/output/<job_id>/` |
| `created_at` | String (ISO 8601) | Set once on job creation. UTC. |
| `updated_at` | String (ISO 8601) | Updated on every status or counter change. UTC. |
| `frame_count` | Integer | Total frames extracted from the video. Updated on extraction completion. |
| `damage_frame_count` | Integer | Frames with at least one damage detection. |
| `blurred_frame_count` | Integer | Frames where at least one licence plate was detected and blurred. |
| `error` | String (nullable) | Set on `failed` status. Describes the stage and error message. |

**DynamoDB table**: `damage-detection-jobs`
**Partition key**: `job_id` (String)
**No sort key.**

**Status transitions** (enforced with `ConditionExpression`):
```
pending → processing  (on pipeline start)
processing → completed  (on successful completion)
processing → failed  (on any unrecoverable error)
pending → failed  (on startup crash recovery — stuck jobs)
processing → failed  (on startup crash recovery — stuck jobs)
```

**Reserved word**: `status` must be aliased as `#status` or `#s` in all DynamoDB expressions.

---

### Frame (in-memory / S3 only — not persisted to DynamoDB)

Frames are not stored as individual DynamoDB records to keep the data model simple in the POC. Frame-level data exists only as:
- Annotated JPEG files in S3 at `s3://<bucket>/output/<job_id>/frame_<index>.jpg`
- Embedded metadata in domain events (see DomainEvent below)

| Attribute | Type | Notes |
|-----------|------|-------|
| `frame_index` | Integer | Zero-based index of the frame in the extracted sequence. |
| `source_fps_position` | Float | Timestamp (seconds) within the original video. |
| `job_id` | String | Reference to parent Job. |
| `damage_detections` | List[BoundingBox] | May be empty. |
| `plates_blurred` | Integer | Count of licence plates blurred in this frame. |

---

### BoundingBox (value object, embedded in events and S3 output)

| Attribute | Type | Notes |
|-----------|------|-------|
| `x1` | Integer | Left pixel coordinate. |
| `y1` | Integer | Top pixel coordinate. |
| `x2` | Integer | Right pixel coordinate. |
| `y2` | Integer | Bottom pixel coordinate. |
| `confidence` | Float | Model confidence score, 0.0–1.0. |
| `label` | String | Detection label (e.g., `"damage"`, `"licence_plate"`). |

---

### DomainEvent (JSON, published to SQS output queue + written to S3)

All domain events share the following envelope:

| Attribute | Type | Notes |
|-----------|------|-------|
| `event_type` | String | One of the types listed below. |
| `job_id` | String | The Job this event relates to. |
| `timestamp` | String (ISO 8601) | UTC timestamp when the event was emitted. |
| `payload` | Object | Event-type-specific data (see below). |

**S3 path**: `s3://<bucket>/events/<job_id>/<event_type>-<timestamp>.json`

**Event types and payloads**:

| Event Type | Payload Fields |
|------------|---------------|
| `JobReceived` | `input_s3_path`, `output_s3_path` |
| `FrameExtractionStarted` | `source_fps`, `target_fps`, `estimated_frame_count` |
| `FrameExtractionCompleted` | `frame_count` |
| `FrameProcessed` | `frame_index`, `source_fps_position`, `damage_detections` (list of BoundingBox), `plates_blurred` |
| `JobCompleted` | `frame_count`, `damage_frame_count`, `blurred_frame_count`, `output_s3_path` |
| `JobFailed` | `failed_at_stage`, `error_message` |
| `JobSkipped` | `reason` (e.g., `"duplicate: job already completed"`) |

---

## Storage Layout

```
s3://<bucket>/
├── input/
│   └── <job_id>/          # Written by external system; triggers pipeline
│       └── video.mp4
├── output/
│   └── <job_id>/          # Written by this application
│       ├── frame_0000.jpg  # Annotated + blurred frame
│       ├── frame_0001.jpg
│       └── ...
└── events/
    └── <job_id>/           # Domain event JSON dump (POC verification)
        ├── JobReceived-2026-04-18T10-00-00Z.json
        ├── FrameExtractionStarted-2026-04-18T10-00-01Z.json
        └── ...
```

---

## DynamoDB Table Schema

```
Table: damage-detection-jobs
Partition key: job_id (String)

Example item:
{
  "job_id": "fleet/vehicle-42/clip.mp4",
  "status": "completed",
  "input_s3_path": "s3://damage-detection/input/fleet/vehicle-42/clip.mp4",
  "output_s3_path": "s3://damage-detection/output/fleet/vehicle-42/clip.mp4/",
  "created_at": "2026-04-18T10:00:00Z",
  "updated_at": "2026-04-18T10:04:32Z",
  "frame_count": 62,
  "damage_frame_count": 14,
  "blurred_frame_count": 3,
  "error": null
}
```

---

## SQS Queues

| Queue | Direction | Purpose |
|-------|-----------|---------|
| `damage-detection-input` | Inbound (S3 → this app) | Receives S3 object-created events for new video files |
| `damage-detection-events` | Outbound (this app → external) | Domain events consumed by the downstream module (out of scope) |

Both are standard queues (not FIFO).
