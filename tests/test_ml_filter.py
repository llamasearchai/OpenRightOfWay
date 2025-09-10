from pathlib import Path

from openrightofway.ml.filter import FalsePositiveFilter, Features


def test_ml_filter_train_and_predict(tmp_path: Path):
    model_path = tmp_path / "baseline.joblib"
    fpf = FalsePositiveFilter(str(model_path))
    fpf.load_or_train()
    assert model_path.exists()

    proba = fpf.predict_proba(Features(area_pixels=2000, magnitude=200.0))
    assert 0.0 <= proba <= 1.0

