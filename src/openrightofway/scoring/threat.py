from __future__ import annotations

from dataclasses import dataclass

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ThreatResult:
    score: float
    level: str
    reasons: list[str]


def _base_by_type(encroachment_type: str) -> float:
    t = encroachment_type.lower()
    mapping = {
        "structure": 40.0,
        "road": 35.0,
        "equipment": 25.0,
        "water": 20.0,
        "unknown": 15.0,
    }
    return mapping.get(t, 15.0)


def compute_threat(
    encroachment_type: str,
    distance_m: float,
    compliance_ok: bool,
    magnitude: float,
    area_pixels: int,
) -> ThreatResult:
    """Compute a 0-100 threat score with qualitative level and reasons."""
    reasons: list[str] = []
    base = _base_by_type(encroachment_type)
    reasons.append(f"base({encroachment_type})={base:.1f}")

    # Distance component: closer => higher score, cap at 50
    if distance_m < 0:
        distance_m = 0
    dist_component = max(0.0, 50.0 * (1.0 - min(distance_m, 100.0) / 100.0))
    reasons.append(f"dist_component={dist_component:.1f} (distance {distance_m:.1f}m)")

    # Magnitude/area component: scale modestly
    mag_component = min(15.0, (magnitude / 255.0) * 10.0)
    area_component = min(10.0, (area_pixels / 1000.0))
    reasons.append(f"mag={mag_component:.1f}")
    reasons.append(f"area={area_component:.1f}")

    # Compliance penalty/bonus
    compliance_component = 10.0 if not compliance_ok else -5.0
    reasons.append("non_compliant +10.0" if not compliance_ok else "compliant -5.0")

    score = base + dist_component + mag_component + area_component + compliance_component
    score = max(0.0, min(100.0, score))

    if score >= 80:
        level = "critical"
    elif score >= 60:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"

    return ThreatResult(score=score, level=level, reasons=reasons)

