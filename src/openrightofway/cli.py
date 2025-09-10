from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from openrightofway.core.config import load_config
from openrightofway.cv.change_detection import detect_changes
from openrightofway.ml.filter import FalsePositiveFilter, Features
from openrightofway.scoring.threat import compute_threat
from openrightofway.compliance.checks import check_setback
from openrightofway.alerts.notifier import Notifier
from openrightofway.integrations.work_orders import WorkOrderManager
from openrightofway.reports.reporting import generate_report
from openrightofway.utils.logging import get_logger
from openrightofway.llm.openai_agent import summarize_events

app = typer.Typer(add_completion=False, help="OpenRightOfWay CLI")
logger = get_logger(__name__)


@app.command()
def train_model(model_path: Optional[str] = typer.Option(None, help="Path to save/load model")):
    """Train or load the baseline ML model used for false positive reduction."""
    cfg = load_config()
    path = model_path or cfg.app.model_path
    fpf = FalsePositiveFilter(model_path=path)
    fpf.load_or_train()
    typer.echo(f"Model ready at {path}")


@app.command()
def detect(
    before: str = typer.Option(..., help="Path to BEFORE image"),
    after: str = typer.Option(..., help="Path to AFTER image"),
    report: Optional[str] = typer.Option(None, help="Path to write JSON report"),
):
    """Run change detection and optionally write a report.

    Note: Without geospatial referencing, distances to pipeline cannot be computed in this command.
    """
    cfg = load_config()
    dets = detect_changes(
        before,
        after,
        change_threshold=cfg.pipeline.change_threshold,
        min_contour_area=cfg.pipeline.min_contour_area,
        morphological_kernel=cfg.pipeline.morphological_kernel,
    )
    result = {
        "before": before,
        "after": after,
        "count": len(dets),
        "detections": [
            {
                "bbox": d.bbox,
                "area": d.area,
                "centroid": d.centroid,
                "magnitude": d.magnitude,
            }
            for d in dets
        ],
    }
    if report:
        generate_report(report, summary="Change detection results", details=result)
        typer.echo(report)
    else:
        typer.echo(json.dumps(result))


@app.command(name="pipeline-run")
def pipeline_run(
    before: str = typer.Option(..., help="Path to BEFORE image"),
    after: str = typer.Option(..., help="Path to AFTER image"),
    encroachment_type: str = typer.Option("unknown", help="Type: structure|road|equipment|water|unknown"),
    latitude: Optional[float] = typer.Option(None, help="Approximate latitude of event center (optional)"),
    longitude: Optional[float] = typer.Option(None, help="Approximate longitude of event center (optional)"),
    report: Optional[str] = typer.Option(None, help="Path to write JSON report"),
):
    """Run end-to-end pipeline: detect -> ML filter -> score -> compliance -> alert -> ticket -> report.

    If latitude/longitude are provided, compliance and distance-sensitive scoring are evaluated.
    """
    cfg = load_config()
    notifier = Notifier()
    wom = WorkOrderManager(cfg.app.work_orders_db)

    # Ensure model is ready
    fpf = FalsePositiveFilter(cfg.app.model_path)
    fpf.load_or_train()

    # Detect
    dets = detect_changes(
        before,
        after,
        change_threshold=cfg.pipeline.change_threshold,
        min_contour_area=cfg.pipeline.min_contour_area,
        morphological_kernel=cfg.pipeline.morphological_kernel,
    )

    # Filter (false-positive reduction)
    kept = []
    for d in dets:
        proba = fpf.predict_proba(Features(area_pixels=d.area, magnitude=d.magnitude))
        if proba >= 0.5:
            kept.append((d, proba))
    logger.info("Kept %d/%d detections after ML filtering", len(kept), len(dets))

    # Score + Compliance
    events = []
    for d, proba in kept:
        distance_m = 100.0
        compliance_ok = True
        if latitude is not None and longitude is not None:
            # In absence of corridor geometry, we treat provided lat/lon as the event location.
            # Distance to pipeline would require corridor geometry; without it we assume distance 100m.
            # Compliance evaluated against setback using this distance estimate.
            distance_m = 100.0  # User can override future versions with corridor input
            compliance_ok = check_setback(distance_m, cfg.compliance).setback_ok

        threat = compute_threat(
            encroachment_type=encroachment_type,
            distance_m=distance_m,
            compliance_ok=compliance_ok,
            magnitude=d.magnitude,
            area_pixels=d.area,
        )
        events.append(
            {
                "bbox": d.bbox,
                "area": d.area,
                "centroid": d.centroid,
                "magnitude": d.magnitude,
                "ml_true_positive_proba": proba,
                "distance_m": distance_m,
                "threat": {
                    "score": threat.score,
                    "level": threat.level,
                    "reasons": threat.reasons,
                },
                "compliance_ok": compliance_ok,
            }
        )

    # Notify and create ticket per high/critical events
    alerts_sent = []
    tickets = []
    for ev in events:
        if ev["threat"]["level"] in {"high", "critical"}:
            msg = (
                f"Encroachment {encroachment_type} detected: score {ev['threat']['score']:.1f} "
                f"level {ev['threat']['level']} at distance {ev['distance_m']:.1f}m"
            )
            # Alerts (if configured)
            # Load recipients from config
            if cfg.alerts.sms.enabled and cfg.alerts.sms.to:
                notifier.send_sms(cfg.alerts.sms.to, msg)
                alerts_sent.append({"type": "sms", "message": msg})
            if cfg.alerts.email.enabled and cfg.alerts.email.to:
                notifier.send_email(cfg.alerts.email.to, subject="OpenRightOfWay Alert", body=msg)
                alerts_sent.append({"type": "email", "message": msg})

            # Ticket
            wo = wom.create(
                title="Encroachment detected",
                description=msg,
                priority="high" if ev["threat"]["level"] == "high" else "critical",
                latitude=latitude,
                longitude=longitude,
                evidence_path=None,
            )
            tickets.append({"id": wo.id, "status": wo.status})

    result = {
        "before": before,
        "after": after,
        "events": events,
        "alerts": alerts_sent,
        "tickets": tickets,
    }

    # Optional LLM summary
    if cfg.llm.enabled:
        try:
            result["summary_nlp"] = summarize_events(result, cfg)
        except Exception as e:
            logger.error("LLM summary failed: %s", e)

    if report:
        path = report
        generate_report(path, summary="Pipeline run", details=result)
        typer.echo(path)
    else:
        typer.echo(json.dumps(result))


@app.command()
def summarize_report(
    report: str = typer.Option(..., help="Path to an existing JSON report"),
    write: bool = typer.Option(False, help="Write a sibling *_summary.txt file instead of printing"),
):
    """Summarize a JSON report using the configured LLM (falls back to deterministic summary)."""
    cfg = load_config()
    p = Path(report)
    data = json.loads(p.read_text(encoding="utf-8"))
    summary = summarize_events(data, cfg)
    if write:
        out = p.with_suffix("")
        out = Path(f"{out}_summary.txt")
        out.write_text(summary, encoding="utf-8")
        typer.echo(str(out))
    else:
        typer.echo(summary)


@app.command()
def alert(
    message: str = typer.Option(..., help="Alert message"),
    sms: bool = typer.Option(False, help="Send SMS via Twilio if configured"),
    email: bool = typer.Option(False, help="Send email via SMTP if configured"),
):
    """Send a manual alert for testing system notifications."""
    cfg = load_config()
    notifier = Notifier()

    if sms and cfg.alerts.sms.to:
        notifier.send_sms(cfg.alerts.sms.to, message)
    if email and cfg.alerts.email.to:
        notifier.send_email(cfg.alerts.email.to, subject="OpenRightOfWay Alert", body=message)
    typer.echo("alert sent (if configured)")


@app.command()
def ticket(
    title: str = typer.Option(...),
    description: str = typer.Option(...),
    priority: str = typer.Option("high"),
):
    """Create a work order ticket in the local database."""
    cfg = load_config()
    wom = WorkOrderManager(cfg.app.work_orders_db)
    wo = wom.create(title=title, description=description, priority=priority)
    typer.echo(json.dumps({"id": wo.id, "status": wo.status}))


@app.command(name="db-serve")
def db_serve(
    port: int = typer.Option(8001, help="Port to serve Datasette on"),
    print_cmd: bool = typer.Option(False, "--print-cmd", help="Print the Datasette command and exit"),
):
    """Serve the work orders SQLite DB with Datasette (if installed)."""
    cfg = load_config()
    db_path = Path(cfg.app.work_orders_db)
    cmd = [
        "datasette",
        "serve",
        str(db_path),
        "--port",
        str(port),
        "--immutable",
        str(db_path),
    ]
    if print_cmd:
        typer.echo(" ".join(cmd))
        return
    # Try to run Datasette if available
    try:
        import shutil
        import subprocess

        if shutil.which("datasette") is None:
            typer.echo("datasette CLI not found. Install with: uv pip install -e .[ops]")
            raise typer.Exit(code=1)
        subprocess.run(cmd, check=True)
    except Exception as e:
        logger.error("Failed to start Datasette: %s", e)
        raise typer.Exit(code=1)

