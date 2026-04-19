# Documentation maintenance

The repo has developer documentation under `docs/` (technologies, architecture, local-setup, testing) with a root `README.md` linking into it. Audience is junior-to-senior developers. Keep it minimal — the intent is essentials only, no bloat.

## When to update

When making changes that affect any of the following, update the corresponding doc in the same change:

- New service, new env var, or changed data flow → `docs/architecture.md` (including the mermaid diagram)
- New/removed library or runtime bump → `docs/technologies.md`
- Changed startup steps, model paths, ports, or `docker-compose.yml` structure → `docs/local-setup.md`
- New test tier or changed test commands → `docs/testing.md`

## Scope

Do not expand scope without being asked — no troubleshooting sections, no per-module deep dives, no API reference tables beyond what exists. If tempted to add a new file, prefer editing an existing one.
