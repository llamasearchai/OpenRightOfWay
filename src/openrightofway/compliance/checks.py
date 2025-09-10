from __future__ import annotations

from dataclasses import dataclass

from openrightofway.core.config import ComplianceSettings


@dataclass
class ComplianceResult:
    setback_ok: bool
    details: str


def check_setback(distance_m: float, cfg: ComplianceSettings) -> ComplianceResult:
    ok = distance_m >= cfg.setback_meters
    details = (
        f"distance {distance_m:.1f}m >= setback {cfg.setback_meters}m"
        if ok
        else f"distance {distance_m:.1f}m < setback {cfg.setback_meters}m"
    )
    return ComplianceResult(setback_ok=ok, details=details)

