# Contributing

## Setup

```bash
python -m pip install -r requirements-dev.txt
pre-commit install        # optional: run lint/format on every commit
```

## Common tasks

Run `make help` for the full list. The important ones:

| Command         | What it does                          |
|-----------------|---------------------------------------|
| `make lint`     | Ruff lint                             |
| `make format`   | Ruff auto-format                      |
| `make test`     | Run the test suite                    |
| `make cov`      | Tests with coverage report + gate     |
| `make data`     | Regenerate the demo dataset           |
| `make up`       | Start the full stack in Docker        |

## Before opening a PR

1. `make format && make lint` — code is clean.
2. `make cov` — tests pass and coverage stays above the gate (85%).
3. Keep KPI logic in `backend/kpis.py` as pure functions (no I/O), and add a
   test for any new KPI in `tests/test_kpis.py`.

CI runs the same checks plus a Docker build, Trivy security scan and a live
integration smoke test.
