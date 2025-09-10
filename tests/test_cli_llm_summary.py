import json
from pathlib import Path

from typer.testing import CliRunner

from openrightofway.cli import app


def test_llm_summarize_report_fallback(tmp_path: Path):
    # Create a minimal report JSON
    report = {
        "before": "b.png",
        "after": "a.png",
        "events": [
            {"threat": {"level": "high", "score": 72.5}, "distance_m": 80.0},
            {"threat": {"level": "low", "score": 25.0}, "distance_m": 120.0},
        ],
        "alerts": [{"type": "sms"}],
        "tickets": [{"id": 1, "status": "open"}],
    }
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report), encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(app, ["summarize-report", "--report", str(p)])
    assert res.exit_code == 0
    out = res.stdout.strip()
    assert "Events:" in out
    assert "High/Critical:" in out

