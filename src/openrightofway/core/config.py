from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AppSettings:
    model_path: str = "models/baseline.joblib"
    reports_dir: str = "reports"
    work_orders_db: str = "work_orders.db"


@dataclass
class PipelineSettings:
    pipeline_buffer_meters: int = 15
    min_contour_area: int = 200
    change_threshold: int = 30
    morphological_kernel: int = 3


@dataclass
class AlertsSMS:
    enabled: bool = False
    to: List[str] = None  # type: ignore[assignment]


@dataclass
class AlertsEmail:
    enabled: bool = False
    to: List[str] = None  # type: ignore[assignment]


@dataclass
class AlertsSettings:
    sms: AlertsSMS = AlertsSMS()
    email: AlertsEmail = AlertsEmail()


@dataclass
class ComplianceSettings:
    setback_meters: int = 15


@dataclass
class ReportingSettings:
    include_images: bool = True


@dataclass
class Config:
    app: AppSettings = AppSettings()
    pipeline: PipelineSettings = PipelineSettings()
    alerts: AlertsSettings = AlertsSettings()
    compliance: ComplianceSettings = ComplianceSettings()
    reporting: ReportingSettings = ReportingSettings()


_DEFAULTS: Dict[str, Any] = {
    "app": {
        "model_path": "models/baseline.joblib",
        "reports_dir": "reports",
        "work_orders_db": "work_orders.db",
    },
    "pipeline": {
        "pipeline_buffer_meters": 15,
        "min_contour_area": 200,
        "change_threshold": 30,
        "morphological_kernel": 3,
    },
    "alerts": {
        "sms": {"enabled": False, "to": []},
        "email": {"enabled": False, "to": []},
    },
    "compliance": {"setback_meters": 15},
    "reporting": {"include_images": True},
}


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            result[k] = _merge_dicts(base[k], v)  # type: ignore[index]
        else:
            result[k] = v
    return result


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        logger.info("Config file %s not found; using defaults", path)
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Config at {path} must be a YAML mapping")
        return data


def ensure_dirs(cfg: Config) -> None:
    reports_dir = Path(cfg.app.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    models_dir = Path(cfg.app.model_path).parent
    models_dir.mkdir(parents=True, exist_ok=True)


def from_dict(d: Dict[str, Any]) -> Config:
    app = d.get("app", {})
    pipeline = d.get("pipeline", {})
    alerts = d.get("alerts", {})
    compliance = d.get("compliance", {})
    reporting = d.get("reporting", {})

    cfg = Config(
        app=AppSettings(**app),
        pipeline=PipelineSettings(**pipeline),
        alerts=AlertsSettings(
            sms=AlertsSMS(**alerts.get("sms", {})),
            email=AlertsEmail(**alerts.get("email", {})),
        ),
        compliance=ComplianceSettings(**compliance),
        reporting=ReportingSettings(**reporting),
    )
    return cfg


def load_config(path: Optional[str] = None) -> Config:
    """Load configuration by merging defaults with a file and env overrides.

    Env overrides (optional):
      - OROW_MODEL_PATH
      - OROW_REPORTS_DIR
      - OROW_WORK_ORDERS_DB
    """
    cfg_path = Path(path) if path else Path("configs/settings.yaml")
    file_cfg = load_yaml(cfg_path)
    merged = _merge_dicts(_DEFAULTS, file_cfg)

    # Environment overrides
    app_overrides: Dict[str, Any] = {}
    if os.getenv("OROW_MODEL_PATH"):
        app_overrides["model_path"] = os.getenv("OROW_MODEL_PATH")
    if os.getenv("OROW_REPORTS_DIR"):
        app_overrides["reports_dir"] = os.getenv("OROW_REPORTS_DIR")
    if os.getenv("OROW_WORK_ORDERS_DB"):
        app_overrides["work_orders_db"] = os.getenv("OROW_WORK_ORDERS_DB")
    if app_overrides:
        merged["app"] = _merge_dicts(merged.get("app", {}), app_overrides)

    cfg = from_dict(merged)
    ensure_dirs(cfg)
    return cfg

