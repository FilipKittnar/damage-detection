<!--
  Sync Impact Report
  ==================
  Version change: 1.0.0 → 1.1.0
  Modified principles:
    - III. Event-Driven, S3-Triggered Pipeline — removed Axon Framework responsibility;
      this application publishes domain events to an output SQS queue consumed by an
      external downstream module. Axon/CQRS implementation is out of scope.
  Added sections: None
  Removed sections: None
  Technology Stack changes:
    - Removed: Java/Kotlin runtime, Axon Framework
    - Added: Python-only runtime, YOLOv8 (damage detection + licence plate detection),
      FastAPI (blurring service), OpenCV, boto3
    - Updated: event output mechanism (SQS output queue + S3 event dump for POC)
  Templates reviewed:
    ✅ .specify/templates/plan-template.md — compatible
    ✅ .specify/templates/spec-template.md — compatible
    ✅ .specify/templates/tasks-template.md — compatible
  Follow-up TODOs: None
-->

# Damage Detection Constitution

## Core Principles

### I. AI-First, Model-Agnostic Design
All damage detection and licence plate blurring logic MUST be implemented behind abstract
model interfaces. Concrete implementations (foundation models or fine-tuned Renault-specific
variants) MUST be swappable without changing pipeline logic. Fine-tuning for Renault vehicle
models is a first-class upgrade path; model interfaces MUST accommodate it from the start.
No pipeline code may depend directly on a specific model artifact or weight file path.

### II. Privacy by Design — Licence Plate Blurring (NON-NEGOTIABLE)
Every output image or video frame MUST have all vehicle licence plates blurred before being
written to any output path or returned to any consumer. Licence plate detection and blurring
runs as a dedicated, independently deployable post-processing service. No output artefact is
considered valid unless the blurring step has been confirmed complete. This rule applies in
all environments, including local development and test runs.

### III. Event-Driven, S3-Triggered Pipeline
Processing MUST be triggered exclusively by S3 object-created events delivered via SQS —
polling is forbidden. Intermediate and final results MUST be persisted to designated S3
output paths. All queryable metadata MUST be stored in DynamoDB. All significant domain
state changes MUST be published as structured JSON events to a dedicated output SQS queue,
which is consumed by an external downstream module outside this project's scope. CQRS and
full event sourcing implementation are the responsibility of that external module, not this
application.

### IV. Test-First Development (NON-NEGOTIABLE)
TDD is mandatory. Tests MUST be written and reviewed before any implementation code is
written. The Red-Green-Refactor cycle is strictly enforced. All ML model interfaces MUST be
mockable for unit tests. Integration tests MUST use Localstack to simulate AWS services.
No implementation is accepted without passing tests covering the relevant acceptance criteria.

### V. Local-First Development
Every service MUST be runnable locally using Localstack and Docker Compose without any
dependency on live AWS infrastructure. Local environment parity with AWS behaviour is a
required quality gate before any merge. Developers MUST be able to trigger, observe, and
debug the full pipeline end-to-end on a local machine.

## Technology Stack

**Runtime language**: Python 3.11+ throughout. This is a Python-only application.

**ML / Computer Vision**:
- Damage detection: YOLOv8 (Ultralytics); ONNX-compatible model interface for portability
  and future fine-tuning with Renault-specific data.
- Licence plate detection and blurring: YOLOv8 (pre-trained licence plate model) +
  OpenCV Gaussian blur; runs as a separate independently deployable service.
- Frame extraction: OpenCV (cv2).

**AWS services**: S3 (video input and processed output artefacts, domain event dump for
POC), DynamoDB (job metadata store), SQS (input trigger queue, domain event output queue).

**Domain event output**: This application publishes domain events as structured JSON
messages to an output SQS queue. The downstream consumer of that queue is outside this
project's scope. As a POC verification mechanism, all outbound events are additionally
written to S3 as JSON files (`s3://<bucket>/events/<job-id>/<event-type>-<timestamp>.json`)
for manual inspection.

**Service HTTP layer**: FastAPI (licence plate blurring service internal API).

**AWS SDK**: boto3.

**Local development**: Localstack (AWS emulation), Docker Compose (full-stack local
orchestration).

**Repository structure**: Monorepo. Two independently deployable Python services:
Pipeline Service and Licence Plate Blurring Service. No API Gateways, no Lambda functions.

## Development Workflow

All new work MUST begin with a written spec and implementation plan before any code is
produced. Feature branches follow the project naming convention. PRs require all tests to
pass and a Localstack smoke-test to succeed before merge.

Model upgrades — including fine-tuned Renault-specific variants — follow the standard
feature branch workflow and MUST include updated and passing tests.

The licence plate blurring service MUST be validated as an independent deployment unit in
every release cycle.

As a POC with future enterprise integration potential, all decisions MUST remain reversible
and interfaces well-defined to support eventual onboarding into the broader Renault Group
platform.

## Governance

This constitution supersedes all other project practices and guidelines. Amendments require
a documented rationale, a semantic version increment, and an updated `Last Amended` date.

- **MAJOR**: Removal or redefinition of a core principle.
- **MINOR**: New principle, new section, or material guidance added.
- **PATCH**: Clarifications, wording fixes, or non-semantic refinements.

All implementation work MUST be verified against this constitution before merge. Added
complexity MUST be justified; YAGNI applies throughout the POC phase.

**Version**: 1.1.0 | **Ratified**: 2026-04-18 | **Last Amended**: 2026-04-18
