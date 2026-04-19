# damage-detection

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
