<!--
  Sync Impact Report
  ==================
  Version change: N/A (initial) → 1.0.0
  Added sections: Core Principles (I–V), Technology Stack, Development Workflow, Governance
  Removed sections: N/A — initial constitution
  Templates reviewed:
    ✅ .specify/templates/plan-template.md — Constitution Check section is generic; compatible
    ✅ .specify/templates/spec-template.md — No conflicts; licence-plate privacy applies as
       a mandatory cross-cutting FR in every feature spec
    ✅ .specify/templates/tasks-template.md — TDD gate already present; aligns with
       Test-First principle; no changes required
  Follow-up TODOs: None — all placeholders resolved
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
Processing MUST be triggered exclusively by S3 object-created events — polling is forbidden.
Intermediate and final results MUST be persisted to designated S3 output paths. All queryable
metadata MUST be stored in DynamoDB. All domain state changes MUST be captured as immutable
domain events following CQRS and Event Sourcing patterns. Axon Framework is the preferred
implementation for event sourcing and command handling where the runtime supports it.

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

**Runtime languages**: Python (ML/CV services), Java or Kotlin (Axon-based orchestration
and event sourcing services). The monorepo is intentionally polyglot.

**ML / Computer Vision**: PyTorch (primary); ONNX-compatible model interfaces for
portability. A separate, independently deployable service handles licence plate detection
and blurring.

**AWS services**: S3 (video input and processed output artefacts), DynamoDB (event store
and queryable metadata), SNS/SQS (event routing between microservices).

**CQRS / Event Sourcing**: Axon Framework (Java/Kotlin services).

**Local development**: Localstack (AWS emulation), Docker Compose (full-stack local
orchestration).

**Repository structure**: Monorepo. Each microservice is independently deployable.
No API Gateways and no Lambda functions.

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

**Version**: 1.0.0 | **Ratified**: 2026-04-18 | **Last Amended**: 2026-04-18
