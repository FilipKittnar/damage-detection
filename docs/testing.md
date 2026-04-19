# Testing

Both services use pytest with `pytest-asyncio` (auto mode). AWS is mocked via `moto` in the pipeline service.

## Install dev dependencies

```bash
# In each service you want to test
cd services/pipeline && pip install -e ".[dev]"
cd services/plate-blurring && pip install -e ".[dev]"
```

## Unit tests

No Docker required.

```bash
cd services/pipeline && python -m pytest tests/unit/ -v
cd services/plate-blurring && python -m pytest tests/unit/ -v
```

## Integration & contract tests

Require the local stack to be running (`docker compose up` from the repo root).

```bash
cd services/pipeline
python -m pytest tests/integration/ -v
python -m pytest tests/contract/ -v
```

## Lint

```bash
ruff check .
```
