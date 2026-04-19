# Damage Detection

An event-driven pipeline that automatically detects vehicle damage in inspection videos and blurs all licence plates in the output. Triggered by S3 object-created events, it extracts frames, runs YOLOv8 damage detection, calls a plate-blurring service, and writes annotated frames plus job metadata back to AWS storage.

## Documentation

- [Technologies](docs/technologies.md) — languages, libraries, infrastructure
- [Architecture](docs/architecture.md) — services, data flow, infrastructure diagram
- [Local setup](docs/local-setup.md) — run the full stack on your machine
- [Testing](docs/testing.md) — run unit, integration, and contract tests

## Repository layout

```text
services/
  pipeline/          # SQS consumer, orchestrator, damage detection
  plate-blurring/    # FastAPI service, YOLOv8 plate detection + blur
infra/localstack/    # LocalStack AWS resource init script
specs/               # Feature specs (Spec Kit)
docs/                # Developer documentation (you are here)
docker-compose.yml   # Full local stack
```

## Development workflow

This project follows [GitHub Spec Kit](https://github.com/github/spec-kit): features are specified, planned, broken into tasks, and implemented through a defined sequence of artifacts before any code is written. Each feature lives in its own folder under `specs/` containing `spec.md`, `plan.md`, `tasks.md`, and supporting design docs.

The workflow is driven by slash commands (`/speckit-specify`, `/speckit-clarify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, `/speckit-analyze`). Before starting a new feature, read the existing `specs/001-mvp-detection-pipeline/` artifacts to see the expected level of detail.
