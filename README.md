# OpenRightOfWay

OpenRightOfWay is a Python monitoring application that leverages computer vision, geospatial analysis, and automated alerting to detect encroachments in pipeline right-of-way corridors and coordinate immediate field response actions.

Key capabilities:
- Multi-source imagery: satellite, aerial surveys, and drone footage
- Change detection (OpenCV) with optional geospatial referencing (rasterio/GDAL)
- Threat assessment scoring based on encroachment type, proximity, and compliance
- Real-time notifications (SMS/email) with GPS coordinates and evidence attachments
- Work order integration for automated ticket creation
- Documentation and reporting suitable for legal/regulatory needs
- Machine learning model for false-positive reduction

## Quickstart (with uv)

Prerequisites:
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

Setup:

```bash
# Create and sync environment
uv venv
uv sync

# Run CLI
uv run orow --help

# Train baseline ML model (synthetic training data)
uv run orow train-model --model-path models/baseline.joblib

# Run a simple change detection and generate a report
uv run orow detect \
  --before path/to/before.png \
  --after path/to/after.png \
  --corridor configs/corridor.geojson \
  --report reports/detection_report.json
```

## Testing

```bash
# Using tox
uv run tox

# Or directly
uv run pytest -q
```

## Configuration

- Default configuration: `configs/settings.yaml`
- Environment variables for alerts (optional):
  - Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`
  - SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`

## Notes on Geospatial Dependencies

`rasterio`/`GDAL` are optional extras used for geo-referencing rasters. If your environment lacks GDAL system libraries, install via your platform package manager (e.g., Homebrew on macOS) or use a geospatial-ready environment (e.g., conda). The core pipeline works without these extras (pixel-space only).

## License

MIT
