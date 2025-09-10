# Repository Guidelines

## Project Structure & Module Organization
- Source: `src/openrightofway/` (modules: `core/`, `cv/`, `geospatial/`, `ml/`, `scoring/`, `alerts/`, `integrations/`, `reports/`, `utils/`).
- CLI: `src/openrightofway/cli.py` exposes `orow` (Typer app).
- Config: `configs/settings.yaml` (env overrides: `OROW_MODEL_PATH`, `OROW_REPORTS_DIR`, `OROW_WORK_ORDERS_DB`).
- Tests: `tests/` with `test_*.py` using PyTest.
- Runtime artifacts: `models/`, `reports/`, `work_orders.db` (created by the app).

## Build, Test, and Development Commands
- Setup env: `uv venv && uv sync --extra dev --extra test`.
- Run CLI: `uv run orow --help` (examples: `orow detect ...`, `orow pipeline-run ...`).
- Lint: `uv run ruff check src tests`.
- Format: `uv run black src tests`.
- Type-check: `uv run mypy src`.
- Tests: `uv run pytest -q` or `uv run tox` (envs: `py310`, `lint`, `type`).
- Package (optional): `uv run python -m build` (PEP 517; wheel/sdist in `dist/`).

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indentation, type hints required for new/changed code.
- Formatting: Black, line length 100. Imports sorted; keep `src/` layout.
- Linting: Ruff rules `E,F,I,UP` (ignore long-lines `E501`). Fix or justify warnings.
- Naming: modules/vars/functions `snake_case`; classes `PascalCase`; CLI flags `kebab-case`.

## Testing Guidelines
- Framework: PyTest with `pytest-cov`. Place tests under `tests/` named `test_*.py`.
- Write focused unit tests for new logic (e.g., dataclasses, pure functions) and CLI tests via Typer’s `CliRunner`.
- Run: `uv run pytest -q` and ensure coverage is not reduced; no strict threshold enforced.

## Commit & Pull Request Guidelines
- Commit style: Conventional Commits (e.g., `feat:`, `docs:`, `chore(ruff):`), imperative mood, concise scope.
- PRs must include: clear description, linked issues, tests for changes, and updates to README/config or CLI help when applicable. Show example commands or output when adding CLI flags.
- Pass CI locally: `uv run tox` before requesting review.

## Security & Configuration Tips
- Secrets via env only: `OPENAI_API_KEY`, `TWILIO_*`, `SMTP_*`, `EMAIL_FROM`. Do not commit keys or credentials.
- Prefer config overrides via `OROW_*` env vars rather than editing `configs/settings.yaml`.
- Avoid committing large generated files; keep artifacts in `models/` and `reports/` out of PR diffs unless essential.

