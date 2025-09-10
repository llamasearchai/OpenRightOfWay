from pathlib import Path

import cv2
import numpy as np
from typer.testing import CliRunner

from openrightofway.cli import app


def test_cli_train_and_detect(tmp_path: Path):
    runner = CliRunner()

    # Train model to a temp location
    model_path = tmp_path / "model.joblib"
    res = runner.invoke(app, ["train-model", "--model-path", str(model_path)])
    assert res.exit_code == 0
    assert model_path.exists()

    # Create synthetic images and run detect with a JSON report
    before = np.zeros((80, 120, 3), dtype=np.uint8)
    after = before.copy()
    cv2.circle(after, (60, 40), 10, (255, 255, 255), -1)

    before_path = tmp_path / "before.png"
    after_path = tmp_path / "after.png"
    cv2.imwrite(str(before_path), before)
    cv2.imwrite(str(after_path), after)

    report_path = tmp_path / "report.json"
    res = runner.invoke(app, [
        "detect",
        "--before", str(before_path),
        "--after", str(after_path),
        "--report", str(report_path)
    ])
    assert res.exit_code == 0
    assert report_path.exists()

