---
description: "Task list for End-to-End MVP Detection Pipeline"
---

# Tasks: End-to-End MVP Detection Pipeline

**Input**: Design documents from `specs/001-mvp-detection-pipeline/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Included throughout — TDD is NON-NEGOTIABLE per project constitution (Principle IV).
Tests MUST be written and confirmed failing before each implementation task.

**Organization**: Tasks grouped by user story for independent implementation and testing.

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- File paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Monorepo scaffolding — directory structure and package initialization for both services.

- [x] T001 Create monorepo directory structure: `services/pipeline/src/pipeline/`, `services/pipeline/tests/{unit,integration,contract}/`, `services/plate-blurring/src/plate_blurring/`, `services/plate-blurring/tests/{unit,integration}/`, `infra/localstack/`
- [x] T002 [P] Create `services/pipeline/pyproject.toml` with dependencies: `ultralytics`, `opencv-python`, `boto3`, `pydantic-settings`, `httpx`, `pytest`, `pytest-asyncio`, `moto[s3,sqs,dynamodb]`
- [x] T003 [P] Create `services/plate-blurring/pyproject.toml` with dependencies: `ultralytics`, `opencv-python`, `fastapi`, `uvicorn[standard]`, `boto3`, `pydantic-settings`, `python-multipart`, `pytest`, `pytest-asyncio`, `httpx`
- [x] T004 [P] Add `__init__.py` files to all packages under `services/pipeline/src/pipeline/` (config, models, models/yolov8, stages, storage)
- [x] T005 [P] Add `__init__.py` files to all packages under `services/plate-blurring/src/plate_blurring/` (config, models, models/yolov8, api)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure components required by all user stories. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: Phases 3–5 cannot start until this phase is complete.

- [x] T006 [P] Create `services/pipeline/src/pipeline/config/settings.py` using `pydantic-settings`: fields `AWS_ENDPOINT_URL` (optional), `AWS_REGION`, `S3_BUCKET`, `SQS_INPUT_QUEUE_URL`, `SQS_EVENTS_QUEUE_URL`, `DYNAMODB_TABLE`, `PLATE_BLURRING_URL`, `FRAME_EXTRACTION_FPS` (float, default 1.0), `DAMAGE_MODEL_PATH`, `DAMAGE_CONFIDENCE` (float, default 0.45)
- [x] T007 [P] Create `services/plate-blurring/src/plate_blurring/config/settings.py` using `pydantic-settings`: fields `PLATE_MODEL_PATH`, `PLATE_CONFIDENCE` (float, default 0.45), `BLUR_KERNEL_SIZE` (int, default 51), `PORT` (int, default 8001)
- [x] T008 [P] Define abstract `Detector` interface in `services/pipeline/src/pipeline/models/interfaces.py`: dataclass `BoundingBox(x1, y1, x2, y2, confidence, label)`, abstract class `Detector` with `detect(image: np.ndarray) -> list[BoundingBox]`
- [x] T009 [P] Define abstract `PlateDetector` interface in `services/plate-blurring/src/plate_blurring/models/interfaces.py`: same `BoundingBox` dataclass, abstract class `PlateDetector` with `detect_and_blur(image: np.ndarray) -> tuple[np.ndarray, list[BoundingBox]]`
- [x] T010 Write unit tests for DynamoDB client in `services/pipeline/tests/unit/test_dynamo_client.py` (using moto): test `create_job` creates record with correct fields and `status=pending`; test `get_job` returns item by job_id; test `update_job_status` transitions status atomically; test `update_job_status` raises on wrong expected current status (ConditionalCheckFailedException); test `update_job_counters` sets frame_count, damage_frame_count, blurred_frame_count — all tests MUST FAIL before T011
- [x] T011 Implement `services/pipeline/src/pipeline/storage/dynamo_client.py`: `create_job(job_id, input_path, output_path)`, `get_job(job_id) -> dict | None`, `update_job_status(job_id, expected_current, new_status, error=None)` with `ConditionExpression` and `#status` alias, `update_job_counters(job_id, frame_count, damage_frame_count, blurred_frame_count)`, `scan_jobs_by_status(status) -> list[dict]`
- [x] T012 [P] Write unit tests for S3 client in `services/pipeline/tests/unit/test_s3_client.py` (using moto): test `download_video` downloads object to a temp file path; test `upload_frame` puts JPEG bytes at correct S3 key (`output/{job_id}/frame_{index:04d}.jpg`); test `write_event_json` puts JSON at correct key (`events/{job_id}/{event_type}-{timestamp}.json`) — all tests MUST FAIL before T013
- [x] T013 [P] Implement `services/pipeline/src/pipeline/storage/s3_client.py`: `download_video(bucket, key) -> Path` (downloads to tempfile), `upload_frame(bucket, job_id, frame_index, jpeg_bytes)`, `write_event_json(bucket, job_id, event_type, payload_dict)`
- [x] T014 Write unit tests for event publisher in `services/pipeline/tests/unit/test_event_publisher.py` (using moto SQS + S3): test `publish` sends JSON message to output SQS queue with correct `event_type`, `job_id`, `timestamp`, `payload`; test `publish` also writes JSON file to S3 events path — tests MUST FAIL before T015
- [x] T015 Implement `services/pipeline/src/pipeline/storage/event_publisher.py`: `publish(event_type, job_id, payload_dict)` — sends JSON to `SQS_EVENTS_QUEUE_URL` and writes to S3 via `s3_client.write_event_json`

**Checkpoint**: Foundational infrastructure complete — user story implementation can now begin.

---

## Phase 3: User Story 1 — Process Incoming Vehicle Video (Priority: P1) 🎯 MVP

**Goal**: Full end-to-end pipeline: S3 event → frame extraction → damage detection → licence plate blurring → annotated frames in S3 + job record in DynamoDB + domain events published.

**Independent Test**: Place a sample MP4 at `s3://damage-detection-local/input/test-job/clip.mp4` in Localstack. After the pipeline processes it, verify: (1) annotated JPEG frames exist at `output/test-job/clip.mp4/`, (2) job record in DynamoDB has `status=completed`, (3) event JSONs exist at `events/test-job/clip.mp4/`.

### Tests for User Story 1 ⚠️ Write first — confirm FAILING before any implementation

- [x] T016 [P] [US1] Write contract test for `POST /v1/blur` in `services/pipeline/tests/contract/test_blur_contract.py`: POST a JPEG with a visible licence plate → assert 200 response, `plates_detected >= 1`, `image_b64` is non-empty, returned image differs from input (plate is blurred)
- [x] T017 [P] [US1] Write contract test for `GET /health` in `services/pipeline/tests/contract/test_blur_health.py`: GET `/health` → assert 200, `status == "ok"`, `model_loaded == true`
- [x] T018 [P] [US1] Write unit tests for frame extractor in `services/pipeline/tests/unit/test_frame_extractor.py`: mock `cv2.VideoCapture` returning a 30fps 3-second video → `extract_frames(fps=1.0)` yields 3 frames with correct `frame_index` (0, 29, 59) and `timestamp_sec` (0.0, 1.0, 2.0); assert memory-safe (no frame accumulation)
- [x] T019 [P] [US1] Write unit tests for damage stage in `services/pipeline/tests/unit/test_damage_stage.py`: mock `Detector.detect()` returning 2 bounding boxes → output frame has boxes drawn (pixel values differ from input at box coordinates); mock `Detector.detect()` returning empty list → output frame equals input
- [x] T020 [P] [US1] Write unit tests for blur stage in `services/pipeline/tests/unit/test_blur_stage.py`: mock `httpx.post` returning 200 with `image_b64` and `plates_detected=1` → returns decoded JPEG bytes; mock `httpx.post` returning 503 → raises `BlurServiceUnavailableError`
- [x] T021 [P] [US1] Write unit tests for output stage in `services/pipeline/tests/unit/test_output_stage.py`: mock `s3_client.upload_frame` → assert called with correct `job_id`, `frame_index`, and JPEG bytes for each frame
- [x] T022 [P] [US1] Write unit tests for YOLOv8 damage detector in `services/pipeline/tests/unit/test_damage_detector.py`: mock `ultralytics.YOLO.__call__` returning a result with 1 bounding box → `detect()` returns a list with 1 `BoundingBox` with correct coordinates and confidence; mock empty result → returns empty list
- [x] T023 [P] [US1] Write unit tests for YOLOv8 plate detector in `services/plate-blurring/tests/unit/test_plate_detector.py`: mock `ultralytics.YOLO.__call__` returning 1 plate bounding box → `detect_and_blur()` returns modified numpy array (blurred at box region) and list with 1 `BoundingBox`; mock empty result → image unchanged
- [x] T024 [P] [US1] Write unit tests for plate blurring API routes in `services/plate-blurring/tests/unit/test_routes.py` (FastAPI `TestClient`): POST `/v1/blur` with valid JPEG + fields → 200 with `image_b64` and `plates_detected`; POST without `file` → 422; GET `/health` when model loaded → 200 `{"status": "ok"}`; GET `/health` when model not loaded → 503

### Implementation for User Story 1

- [x] T025 [P] [US1] Implement `services/pipeline/src/pipeline/models/yolov8/damage_detector.py`: class `YoloV8DamageDetector(Detector)`, loads `.pt` model from `settings.DAMAGE_MODEL_PATH`, `detect(image)` calls `model(image, conf=settings.DAMAGE_CONFIDENCE)`, returns `list[BoundingBox]` from `results[0].boxes.xyxy`
- [x] T026 [P] [US1] Implement `services/pipeline/src/pipeline/stages/frame_extractor.py`: `extract_frames(video_path, fps) -> Generator[FrameData, None, None]` — opens with `cv2.VideoCapture`, computes `frame_skip = floor(source_fps / fps)`, yields `FrameData(frame_index, timestamp_sec, bgr_array)` at each skip interval, never accumulates frames in memory, releases capture on completion
- [x] T027 [US1] Implement `services/pipeline/src/pipeline/stages/damage_stage.py`: `DamageStage(detector: Detector)` — `process(frame_data) -> AnnotatedFrameData`: calls `detector.detect(rgb_array)`, draws each `BoundingBox` on the frame as a coloured rectangle with `cv2.rectangle`, returns annotated frame + detections list
- [x] T028 [US1] Implement `services/pipeline/src/pipeline/stages/blur_stage.py`: `BlurStage(blurring_url)` — `process(annotated_frame_data, job_id, frame_index) -> BlurredFrameData`: POSTs frame JPEG to `{blurring_url}/v1/blur` via `httpx`, decodes `image_b64` from JSON response, raises `BlurServiceUnavailableError` on non-200 (depends on T027)
- [x] T029 [US1] Implement `services/pipeline/src/pipeline/stages/output_stage.py`: `OutputStage(s3_client)` — `process(blurred_frame_data, job_id, frame_index)`: encodes frame to JPEG with `cv2.imencode`, calls `s3_client.upload_frame(bucket, job_id, frame_index, jpeg_bytes)` (depends on T028)
- [x] T030 [P] [US1] Implement `services/plate-blurring/src/plate_blurring/models/yolov8/plate_detector.py`: class `YoloV8PlateDetector(PlateDetector)`, loads model from `settings.PLATE_MODEL_PATH`, `detect_and_blur(image)`: runs inference, for each detected plate box applies `cv2.GaussianBlur` with `(settings.BLUR_KERNEL_SIZE, settings.BLUR_KERNEL_SIZE)` to the region, returns blurred image + `list[BoundingBox]`
- [x] T031 [P] [US1] Implement `services/plate-blurring/src/plate_blurring/api/app.py`: FastAPI application factory with lifespan that loads `YoloV8PlateDetector` on startup and stores on `app.state.detector`; exposes `app` instance
- [x] T032 [US1] Implement `services/plate-blurring/src/plate_blurring/api/routes.py`: `POST /v1/blur` — decodes uploaded file bytes to numpy array via `cv2.imdecode`, calls `app.state.detector.detect_and_blur(image)`, returns JSON `{image_b64, plates_detected, bounding_boxes}`; `GET /health` — returns `{"status": "ok", "model_loaded": true}` if detector loaded, 503 otherwise (depends on T030, T031)
- [x] T033 [P] [US1] Implement `services/plate-blurring/src/plate_blurring/main.py`: `uvicorn.run(app, host="0.0.0.0", port=settings.PORT)`
- [x] T034 [US1] Implement `services/pipeline/src/pipeline/consumer.py`: `SqsConsumer(sqs_client, queue_url, handler_fn)` — `consume()` loop: `receive_message(WaitTimeSeconds=20, MaxNumberOfMessages=1)`, filters `s3:TestEvent`, parses `Records[0].s3`, `unquote_plus` on key, derives `job_id = key.removeprefix("input/")`, starts visibility heartbeat thread (`change_message_visibility` every 60s), calls `handler_fn(bucket, key, job_id)`, deletes message on success, leaves in queue on exception
- [x] T035 [US1] Implement `services/pipeline/src/pipeline/orchestrator.py`: `Orchestrator` — `process_job(bucket, key, job_id)`: (1) idempotency check (`get_job` → skip + log if status=completed); (2) `create_job`, publish `JobReceived`; (3) update status to `processing`, publish `FrameExtractionStarted`; (4) download video from S3; (5) iterate `frame_extractor.extract_frames()` → `damage_stage.process()` → `blur_stage.process()` → `output_stage.process()`; (6) accumulate counters; (7) update status to `completed`, update counters, publish `JobCompleted`; on any exception → update status to `failed`, publish `JobFailed`; cleanup temp file
- [x] T036 [US1] Write integration test for full pipeline end-to-end in `services/pipeline/tests/integration/test_pipeline_e2e.py` (requires Localstack + plate-blurring service running): upload sample video to `input/test-job/clip.mp4`, invoke `orchestrator.process_job()` directly, assert output frames exist in S3 at `output/test-job/clip.mp4/`, assert job record has `status=completed` and `frame_count > 0`, assert event JSONs exist at `events/test-job/clip.mp4/`

**Checkpoint**: User Story 1 fully functional and independently testable.

---

## Phase 4: User Story 2 — Monitor Job Status (Priority: P2)

**Goal**: Job lifecycle is fully visible — status transitions, counters, and error descriptions are reliably persisted to DynamoDB and recoverable after a service crash.

**Independent Test**: Run a job through the pipeline, query DynamoDB at each stage with `dynamo_client.get_job()`, verify `status` transitions match `pending → processing → completed` with non-null timestamps; run a failing job, verify `status=failed` with `error` field populated.

### Tests for User Story 2 ⚠️ Write first — confirm FAILING before any implementation

- [x] T037 [P] [US2] Write unit tests for startup crash recovery in `services/pipeline/tests/unit/test_startup_recovery.py` (moto): seed DynamoDB with 2 jobs in `processing` state and 1 in `completed`; call `recover_stuck_jobs()`; assert the 2 processing jobs now have `status=failed` and `error` field set; assert completed job is unchanged
- [x] T038 [P] [US2] Write integration test for job status tracking in `services/pipeline/tests/integration/test_job_status.py` (Localstack): run `orchestrator.process_job()` on a valid video; query DynamoDB at completion; assert `frame_count`, `damage_frame_count`, `blurred_frame_count` are integers ≥ 0; run `process_job()` with a corrupted video path; assert job has `status=failed` and non-empty `error`

### Implementation for User Story 2

- [x] T039 [US2] Add `recover_stuck_jobs()` to `services/pipeline/src/pipeline/orchestrator.py`: calls `dynamo_client.scan_jobs_by_status("processing")` + `scan_jobs_by_status("pending")`; for each result calls `update_job_status(job_id, current, "failed", error="Service restarted mid-job; re-trigger via SQS replay")`
- [x] T040 [US2] Implement `services/pipeline/src/pipeline/main.py`: on startup (1) call `orchestrator.recover_stuck_jobs()`; (2) verify plate-blurring service health via `GET /health` — exit with error if unreachable; (3) start `SqsConsumer.consume()` loop

**Checkpoint**: User Stories 1 and 2 independently functional and testable.

---

## Phase 5: User Story 3 — Run the Full Pipeline Locally (Priority: P3)

**Goal**: The entire system starts with a single `docker compose up` command. No live AWS credentials required. A developer can trigger, observe, and validate the full pipeline locally.

**Independent Test**: Run `docker compose up --build`; wait for all services healthy; upload a sample video to Localstack S3; wait; verify annotated frames in S3 output bucket and job record in DynamoDB.

### Tests for User Story 3 ⚠️ Write first — confirm FAILING before any implementation

- [x] T041 [US3] Write integration test for local environment in `services/pipeline/tests/integration/test_local_env.py` (requires Docker Compose running): assert Localstack responds at `http://localhost:4566`; assert S3 bucket `damage-detection-local` exists; assert SQS queues `damage-detection-input` and `damage-detection-events` exist; assert DynamoDB table `damage-detection-jobs` exists; assert plate-blurring health endpoint returns 200

### Implementation for User Story 3

- [x] T042 Create `infra/localstack/init-aws.sh`: (1) create S3 bucket `damage-detection-local`; (2) create SQS standard queue `damage-detection-input` with IAM policy granting `sqs:SendMessage` to `s3.amazonaws.com`; (3) create SQS standard queue `damage-detection-events`; (4) configure S3 bucket notification to send `s3:ObjectCreated:*` events (prefix `input/`) to `damage-detection-input` queue ARN (`arn:aws:sqs:us-east-1:000000000000:damage-detection-input`); (5) create DynamoDB table `damage-detection-jobs` with partition key `job_id` (String)
- [x] T043 [P] Create `services/pipeline/Dockerfile`: `FROM python:3.11-slim`, install system deps (`libgl1` for OpenCV), `COPY pyproject.toml`, `RUN pip install -e .`, `COPY src/`, `CMD ["python", "-m", "pipeline.main"]`
- [x] T044 [P] Create `services/plate-blurring/Dockerfile`: `FROM python:3.11-slim`, install system deps, `COPY pyproject.toml`, `RUN pip install -e .`, `COPY src/`, `CMD ["python", "-m", "plate_blurring.main"]`
- [x] T045 Create `docker-compose.yml`: define `localstack` service (image `localstack/localstack:3`, ports `4566`, env `SERVICES=s3,sqs,dynamodb`, volume mount `infra/localstack/init-aws.sh:/etc/localstack/init/ready.d/init-aws.sh`); define `plate-blurring` service (build `services/plate-blurring`, port `8001`, volume mount for model weights at `/app/models/`, healthcheck `GET /health`); define `pipeline` service (build `services/pipeline`, env vars for Localstack endpoints, `depends_on` localstack and plate-blurring, volume mount for damage model weights)

**Checkpoint**: All three user stories independently functional and testable locally.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Structural improvements affecting all services and user stories.

- [x] T046 [P] Add structured JSON logging to `services/pipeline/src/pipeline/` — configure Python `logging` with a JSON formatter in `settings.py`; add `logger` calls at each pipeline stage transition (job received, frame extracted, damage detected, frame blurred, frame uploaded, job completed/failed)
- [x] T047 [P] Add structured JSON logging to `services/plate-blurring/src/plate_blurring/` — log each `/v1/blur` request (job_id, frame_index, plates_detected, duration_ms) and any model errors
- [x] T048 Review and harden edge case handling in `services/pipeline/src/pipeline/stages/` and `orchestrator.py`: invalid video format → `JobFailed` with descriptive error; video with zero frames → `JobFailed`; model inference error → `JobFailed`; `BlurServiceUnavailableError` → `JobFailed` (never partial output); ensure temp file cleanup runs even on exception
- [x] T049 Validate `specs/001-mvp-detection-pipeline/quickstart.md` against the running local environment — run all steps in quickstart.md from scratch, note any discrepancies, update quickstart.md to match actual behaviour

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 — tests first, then implementation
- **Phase 4 (US2)**: Depends on Phase 2; integrates with Phase 3 outputs
- **Phase 5 (US3)**: Depends on Phase 3 + Phase 4 (needs working pipeline to test locally)
- **Phase 6 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: Can start immediately after Foundational — no dependency on US2 or US3
- **US2 (P2)**: Depends on Foundational; integrates with US1 outputs (dynamo_client, orchestrator)
- **US3 (P3)**: Depends on US1 + US2 being complete (Docker setup wraps the working pipeline)

### Within Each User Story

1. Write ALL tests for the story first — confirm they FAIL
2. Implement in dependency order: interfaces → models → stages → consumer/orchestrator → entrypoint
3. Verify all tests pass before marking story complete
4. Commit after story completion checkpoint

---

## Parallel Opportunities

### Phase 1 (all parallelizable)
```
T001 → then T002, T003, T004, T005 in parallel
```

### Phase 2
```
T006, T007, T008, T009, T010, T011, T012, T013 (T008 before T011, T010 before T013)
T014 → T015 (sequential)
```

### Phase 3 — Tests (all parallelizable after Phase 2)
```
T016, T017, T018, T019, T020, T021, T022, T023, T024 — all in parallel
```

### Phase 3 — Implementation
```
T025, T026, T030, T031 in parallel →
T027 (depends T025, T026) →
T028 (depends T027), T032 (depends T030, T031) in parallel →
T029 (depends T028) →
T033, T034 in parallel →
T035 (depends T034) →
T036
```

### Phase 4 — Tests (parallelizable)
```
T037, T038 in parallel
```

### Phase 5 — Implementation
```
T042 → T043, T044 in parallel → T045
```

### Phase 6
```
T046, T047 in parallel → T048 → T049
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Write all US1 tests (T016–T024), confirm FAILING
4. Complete Phase 3: US1 implementation (T025–T035)
5. **STOP and VALIDATE**: Run US1 integration test (T036) independently
6. Confirm: frames in S3, job in DynamoDB, events published

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 → core pipeline working (MVP)
3. US2 → crash recovery + reliable status tracking
4. US3 → fully dockerised, local-first dev environment
5. Polish → production-quality logging and error handling

---

## Notes

- `[P]` = safe to run in parallel (different files, no incomplete dependencies)
- Constitution Principle IV is non-negotiable: tests MUST fail before implementation starts
- Model weight files (`.pt`) are NOT committed to the repo — provide download instructions in `services/pipeline/README.md` and `services/plate-blurring/README.md`
- `status` is a DynamoDB reserved word — always alias as `#status` in expressions (see research.md)
- Always `unquote_plus()` S3 object keys from SQS event messages (see research.md)
- `cv2.GaussianBlur` kernel size must be an odd integer (51 recommended for sufficient obfuscation)
- Localstack SQS ARN format: `arn:aws:sqs:us-east-1:000000000000:<queue-name>`
