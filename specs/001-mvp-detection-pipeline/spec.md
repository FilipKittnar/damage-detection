# Feature Specification: End-to-End MVP Detection Pipeline

**Feature Branch**: `001-mvp-detection-pipeline`
**Created**: 2026-04-18
**Status**: Draft
**Input**: User description: "End-to-End MVP Detection Pipeline — single vertical slice proving the full concept from S3 upload trigger to annotated output frames back in S3."

## Clarifications

### Session 2026-04-18

- Q: How should S3 object-created events reach this application? → A: S3 → SQS directly (no SNS fanout layer).
- Q: What should happen when a job ID has already been fully processed (output already exists)? → A: Skip and log — discard the duplicate SQS message and record the skip in the job log; do not reprocess.
- Q: If the pipeline crashes mid-job, what happens on service recovery? → A: Jobs stuck in `processing` state are marked `failed` on startup; operator re-triggers by replaying the SQS event.
- Q: How should Job ID be derived from the S3 object key? → A: Full S3 key minus the `/input/` prefix (e.g. key `input/fleet/vehicle-42/clip.mp4` → job ID `fleet/vehicle-42/clip.mp4`).
- Q: Where is the frame extraction rate configured? → A: Global application config only — single environment-level setting, same rate for all jobs; no per-job override.

## User Scenarios & Testing _(mandatory)_

### User Story 1 — Process Incoming Vehicle Video (Priority: P1)

An external system places a vehicle inspection video at the designated S3 input path.
This application automatically detects the new file via an S3 event, processes the video,
identifies damaged areas on the vehicle, blurs all licence plates in every output frame,
and saves annotated images to the S3 output path. This application does not handle or
initiate the video upload — that is the responsibility of the external system.

**Why this priority**: This is the core value of the entire system. Without end-to-end
video processing and output delivery, nothing else matters.

**Independent Test**: Can be fully tested by placing a sample MP4 at the input bucket
path (simulating the external system) and verifying that annotated frames with bounding
boxes appear in the output path and that no licence plate is visible in any output image.

**Acceptance Scenarios**:

1. **Given** a valid vehicle inspection video has been placed at `s3://<bucket>/input/<job-id>/`
   by an external system,
   **When** the S3 object-created event fires,
   **Then** the pipeline starts processing within 30 seconds, extracts all frames,
   runs damage detection, blurs all licence plates, and saves annotated frames to
   `s3://<bucket>/output/<job-id>/`.

2. **Given** a video containing visible vehicle damage,
   **When** processing completes,
   **Then** every output frame with detected damage has at least one bounding box
   highlighting the damaged area.

3. **Given** a video containing one or more visible vehicle licence plates,
   **When** processing completes,
   **Then** every output frame has all licence plates blurred and no licence plate
   text is legible.

4. **Given** a video file has appeared in the input path,
   **When** processing completes (success or failure),
   **Then** a job record with status, frame count, damage detections, and timestamps
   is persisted and queryable.

---

### User Story 2 — Monitor Job Status (Priority: P2)

An operator wants to know whether a submitted job is still processing, has completed
successfully, or has failed, and to see basic statistics about what was found.

**Why this priority**: Without status visibility, the operator has no way to know if
the system worked or where it failed. Critical for debugging the POC.

**Independent Test**: Can be tested by querying job metadata after a known video file
has been detected in the input bucket and verifying that status transitions
(pending → processing → completed/failed) are recorded with timestamps.

**Acceptance Scenarios**:

1. **Given** a video file has been detected in the input path and a job has been created,
   **When** the operator queries the job record,
   **Then** the record shows the current status and the time it entered that status.

2. **Given** a job has completed successfully,
   **When** the operator queries the job record,
   **Then** the record shows total frames extracted, number of frames with detected damage,
   and number of frames where licence plates were blurred.

3. **Given** a job has failed at any pipeline stage,
   **When** the operator queries the job record,
   **Then** the record shows which stage failed and an error description.

---

### User Story 3 — Run the Full Pipeline Locally (Priority: P3)

A developer wants to run the entire pipeline on their local machine — including S3 triggers,
video processing, damage detection, licence plate blurring, and output storage — without
connecting to any live AWS infrastructure.

**Why this priority**: Local runnability is a constitution-level requirement and is
essential for iterative development and testing of the POC.

**Independent Test**: Can be tested by starting the local environment with a single
command, placing a sample video in the local input S3 bucket to simulate the external
system, and verifying that annotated output frames appear in the local output bucket.

**Acceptance Scenarios**:

1. **Given** Docker and Docker Compose are installed,
   **When** the developer runs the local startup command,
   **Then** all services start successfully and are reachable within 2 minutes.

2. **Given** the local environment is running,
   **When** a video file is placed in the local input bucket (simulating the external system),
   **Then** the pipeline executes end-to-end using the same code paths as production,
   and annotated output frames appear in the local output bucket.

3. **Given** the local environment is running,
   **When** a developer inspects logs,
   **Then** each pipeline stage emits structured log entries showing progress and any errors.

---

### Edge Cases

- What happens when the file placed in the input path is not a valid video format?
- What happens when the video contains no detectable vehicle (e.g., blank recording)?
- What happens when no damage is detected? (Output frames should still be saved, unmodified except for licence plate blurring.)
- What happens when no licence plates are found? (Processing continues normally; blurring step is a no-op.)
- What happens when the video is very long (e.g., > 30 minutes / thousands of frames)?
- What happens when the damage detection model is unavailable or returns an error?
- What happens when the licence plate blurring service is unavailable? (Pipeline MUST NOT produce unblurred output — it must fail safely.)
- What happens when the S3 output path already contains results for the same job ID? → The pipeline checks for an existing completed job record before processing. If one is found, the duplicate event is discarded and the skip is logged. No reprocessing occurs.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST start processing automatically when a video file appears at the designated S3 input path. S3 object-created events are delivered directly to an SQS queue; this application consumes messages from that queue to trigger the pipeline. This application does not perform or initiate uploads.
- **FR-002**: The system MUST extract individual frames from the video file.
- **FR-003**: The system MUST run a damage detection model on each extracted frame and produce bounding box annotations for detected damage areas.
- **FR-004**: The system MUST run licence plate detection and blurring on every output frame before saving. Frames with unblurred licence plates MUST NOT be written to the output path.
- **FR-005**: The system MUST save all annotated output frames to the designated S3 output path under the same job identifier as the input.
- **FR-006**: The system MUST persist a job record to DynamoDB containing: job ID, input path, output path, status, timestamps, frame count, damage detection count, and blurring count.
- **FR-007**: The system MUST update the job record status as processing progresses through each pipeline stage (pending → processing → completed or failed).
- **FR-008**: The system MUST publish a structured JSON domain event to a dedicated output SQS queue for each significant pipeline state change. Full CQRS/Event Sourcing implementation is the responsibility of an external downstream module outside this project's scope. As a POC verification mechanism, every outbound event MUST also be written as a JSON file to `s3://<bucket>/events/<job-id>/` so correctness can be confirmed by inspection.
- **FR-009**: The entire pipeline MUST be runnable locally using Docker Compose and a local AWS emulator, without connecting to live AWS.
- **FR-010**: If the licence plate blurring service is unavailable or returns an error, the pipeline MUST fail the job rather than produce output with visible licence plates.
- **FR-011**: The pipeline MUST be idempotent with respect to job ID. If a completed job record already exists for a given job ID when an SQS message is consumed, the message MUST be discarded and the skip MUST be logged. No reprocessing occurs.
- **FR-012**: On service startup, the system MUST detect any jobs left in `processing` state (indicating a prior crash) and transition them to `failed` with an appropriate error description. Recovery from mid-job crashes requires manual operator re-trigger via SQS message replay.

### Key Entities

- **Job**: Represents a single video processing request. Attributes: job ID (S3 key minus `/input/` prefix, e.g. `fleet/vehicle-42/clip.mp4`), input S3 path, output S3 path, status, created-at, updated-at, frame count, damage frame count, blurred frame count, error (if failed).
- **Frame**: A single extracted image from the video. Attributes: frame index, timestamp-in-video, source job ID, damage detections (list of bounding boxes), licence plates blurred (count).
- **DamageDetection**: A bounding box indicating a detected damage area on a frame. Attributes: frame reference, bounding box coordinates, confidence score.
- **DomainEvent**: An immutable record of a state change. Types: `JobSubmitted`, `FrameExtractionStarted`, `FrameExtractionCompleted`, `DamageDetectionCompleted`, `LicencePlateBlurringCompleted`, `JobCompleted`, `JobFailed`.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A video placed in the input bucket by an external system results in annotated output frames appearing in the output bucket within a time proportional to video length (target: under 5 minutes for a 1-minute video on local hardware).
- **SC-002**: 100% of output frames with originally visible licence plates have those plates blurred — zero legible plates in any output image.
- **SC-003**: The full pipeline can be started and run entirely on a developer's local machine without any live cloud credentials or external service dependencies.
- **SC-004**: Job status is queryable and reflects the correct processing stage within 5 seconds of each stage transition.
- **SC-005**: The system correctly identifies and annotates damage in at least the obvious damage areas of a reference test video (qualitative validation for POC).
- **SC-006**: A failed job (any stage) leaves a queryable error record — no silent failures.

## Assumptions

- The input video format is MP4, WEBM or MOV. Other formats are out of scope for the POC.
- Frame extraction rate is set via global application configuration (environment variable or config file) and applies uniformly to all jobs. The default is 1 frame per second. No per-job override is supported in this version.
- The damage detection model used is a pre-trained foundation model (e.g., a general object/damage detection model); no fine-tuning is in scope for this spec.
- The licence plate detection and blurring model is also a pre-trained foundation model.
- A single S3 bucket is used for both input and output, distinguished by path prefix (`/input/` vs `/output/`).
- Video file upload to the S3 input path is the sole responsibility of an external application. This system does not handle, initiate, or control uploads — it only reacts to S3 object-created events.
- S3 object-created events are delivered directly from S3 to an SQS queue (no SNS fanout). This application polls or reacts to that SQS queue as its pipeline entry point.
- Job ID is derived from the S3 object key by stripping the `/input/` prefix (e.g. S3 key `input/fleet/vehicle-42/clip.mp4` → job ID `fleet/vehicle-42/clip.mp4`). The output path is constructed as `output/<job-id>/`.
- There is no authentication or authorisation layer in the POC — the pipeline is triggered purely by S3 events.
- DynamoDB is used as the queryable job metadata store. There is no Axon event store in this application; full event sourcing is the responsibility of an external downstream module.
- This application is Python-only. No Java or Kotlin components are in scope.
- The pipeline is designed for sequential single-job processing in the POC; parallel multi-job processing is a future concern.
- Output frames are saved as JPEG or PNG images; video reconstruction from frames is out of scope.
