from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Features:
    area_pixels: int
    magnitude: float

    def as_array(self) -> np.ndarray:
        return np.array([[float(self.area_pixels), float(self.magnitude)]], dtype=float)


class FalsePositiveFilter:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.clf: Pipeline | None = None

    def load_or_train(self) -> None:
        p = Path(self.model_path)
        if p.exists():
            self.clf = joblib.load(p)
            logger.info("Loaded ML filter model from %s", p)
        else:
            logger.info("Model not found at %s; training baseline model", p)
            self.clf = self._train_baseline()
            p.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(self.clf, p)
            logger.info("Saved baseline model to %s", p)

    def _train_baseline(self) -> Pipeline:
        # Synthetic training data: area and magnitude with some noise
        rng = np.random.default_rng(42)
        n = 400
        area = rng.integers(50, 5000, size=n)
        mag = rng.uniform(0, 255, size=n)
        # True positive heuristic: larger area and higher magnitude
        logits = 0.001 * (area - 500) + 0.02 * (mag - 30) + rng.normal(0, 0.5, size=n)
        y = (logits > 0.0).astype(int)
        X = np.column_stack([area.astype(float), mag.astype(float)])

        clf = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("lr", LogisticRegression(max_iter=1000)),
            ]
        )
        clf.fit(X, y)
        return clf

    def predict_proba(self, feats: Features) -> float:
        if self.clf is None:
            raise RuntimeError("Model not loaded; call load_or_train() first")
        proba = float(self.clf.predict_proba(feats.as_array())[0, 1])
        return proba

