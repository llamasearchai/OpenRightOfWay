# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

- Repository: OpenRightOfWay (Python 3.10+, src-layout package: openrightofway)
- Primary tooling: uv (venv/run/build), tox (test/lint/type), pytest, ruff, black, mypy
- Entry point: CLI script "orow" (Typer app)

Common commands
- One-time setup (uses uv):
  - uv venv
  - uv sync
- Run the CLI:
  - uv run orow --help
  - Detect changes and write a JSON report:
    - uv run orow detect --before path/to/before.png --after path/to/after.png --report reports/detection_report.json
  - Train or load the baseline ML model:
    - uv run orow train-model --model-path models/baseline.joblib
  - End-to-end pipeline (detect -> ML filter -> score -> compliance -> alert -> ticket -> report):
    - uv run orow pipeline-run --before before.png --after after.png --encroachment-type structure --latitude 29.75 --longitude -95.35 --report reports/pipeline_run.json
  - Send test alerts (if configured via env):
    - uv run orow alert --message "Test alert" --sms --email
  - Create a local work-order ticket:
    - uv run orow ticket --title "Encroachment" --description "Manual ticket" --priority high
- Tests:
  - Run all via tox (includes coverage): uv run tox
  - Just unit tests: uv run pytest -q
  - Run a single file: uv run pytest tests/test_change_detection.py -q
  - Run a single test function: uv run pytest tests/test_change_detection.py::test_detect_changes -q
  - Filter by name: uv run pytest -k "scoring and not slow" -q
- Lint/format/type (two equivalent ways):
  - Via tox envs (works even if dev tools aren’t installed in the base venv):
    - Lint: uv run tox -e lint
    - Type-check: uv run tox -e type
  - Direct tools (require dev extras to be installed):
    - Lint: uv run ruff check src tests
    - Format (check): uv run black --check src tests
    - Format (apply): uv run black src tests
    - Type-check: uv run mypy src
- Build (PEP 517 via hatchling):
  - uv build  # creates dist/*.whl and dist/*.tar.gz

Configuration and environment
- Primary config file: configs/settings.yaml (merged with safe defaults and optional env overrides)
- Env overrides recognized by the app (see core/config.py):
  - OROW_MODEL_PATH, OROW_REPORTS_DIR, OROW_WORK_ORDERS_DB
- Alerts (optional) via environment variables (see alerts/notifier.py):
  - Twilio SMS: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM
  - SMTP Email: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM
- Optional extras defined in pyproject:
  - geo (rasterio, GDAL), alerts (twilio), test (pytest, pytest-cov), dev (ruff, black, mypy, tox)
  - If you need direct tool invocations (ruff/black/mypy), install dev extras: uv pip install -e .[dev]

High-level architecture
- CLI (Typer) — src/openrightofway/cli.py
  - Commands: train-model, detect, pipeline-run, alert, ticket
  - detect: runs image change detection and optionally writes a JSON report
  - pipeline-run: end-to-end flow — detect -> ML filter -> threat scoring -> compliance check -> notifications -> work-order ticket -> report
- Configuration — src/openrightofway/core/config.py
  - Loads configs/settings.yaml; merges with in-code defaults and OROW_* env overrides; ensures reports/models directories exist
- Computer Vision — src/openrightofway/cv/change_detection.py
  - OpenCV absdiff + threshold + morphology + contour extraction; returns Detection objects (bbox, area, centroid, magnitude)
- ML False-Positive Filter — src/openrightofway/ml/filter.py
  - Baseline logistic regression (sklearn Pipeline with StandardScaler) trained on synthetic features: area_pixels, magnitude; persisted via joblib at models/baseline.joblib
- Threat Scoring — src/openrightofway/scoring/threat.py
  - Combines encroachment type base score, distance-to-pipeline component, magnitude and area components, and compliance penalty/bonus; outputs score (0-100) and level (low/medium/high/critical)
- Compliance — src/openrightofway/compliance/checks.py
  - Simple setback check vs configured setback_meters
- Alerts — src/openrightofway/alerts/notifier.py
  - SMS via Twilio and email via SMTP (falls back to logging when not configured)
- Work Orders — src/openrightofway/integrations/work_orders.py
  - Local SQLite-backed ticketing (create/get/update)
- Geospatial Utilities — src/openrightofway/geospatial/geo.py
  - Corridor loading from GeoJSON, UTM projection helpers, distance-to-corridor, and buffer containment checks (Shapely + pyproj)
- Reporting — src/openrightofway/reports/reporting.py
  - JSON report writer used by detect/pipeline-run
- Logging — src/openrightofway/utils/logging.py
  - Root logging setup using RichHandler when available

Notes and caveats
- The detect command intentionally does not compute geospatial distances; pipeline-run accepts latitude/longitude and currently uses a fixed 100m proxy distance when corridor geometry isn’t supplied. Use geospatial/geo.py for corridor-aware distance computations when integrating corridor inputs.
- Geospatial extras (rasterio/GDAL) are optional; the core pipeline runs without them (pixel-space only).

Sources of truth
- pyproject.toml: build backend (hatchling), dependencies, CLI script, ruff/black/mypy/pytest config
- tox.ini: test (with coverage), lint (ruff), type (mypy) environments
- README.md: quickstart with uv and basic examples
- configs/settings.yaml: default application settings
- tests/: quick coverage for CLI, CV detection, ML filter, and scoring

