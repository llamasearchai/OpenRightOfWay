from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    area: int
    centroid: Tuple[float, float]
    magnitude: float  # mean abs diff inside bbox


def _preprocess(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    return gray


def detect_changes(
    before_path: str,
    after_path: str,
    change_threshold: int = 30,
    min_contour_area: int = 200,
    morphological_kernel: int = 3,
) -> List[Detection]:
    """Detect changes between two images using absdiff + thresholding.

    Returns a list of Detection objects with bounding boxes and basic metrics.
    """
    before = cv2.imread(before_path, cv2.IMREAD_COLOR)
    after = cv2.imread(after_path, cv2.IMREAD_COLOR)

    if before is None or after is None:
        raise FileNotFoundError("Could not read one or both images for change detection")

    if before.shape[:2] != after.shape[:2]:
        after = cv2.resize(after, (before.shape[1], before.shape[0]))

    g1 = _preprocess(before)
    g2 = _preprocess(after)

    diff = cv2.absdiff(g1, g2)
    _, thresh = cv2.threshold(diff, change_threshold, 255, cv2.THRESH_BINARY)

    kernel = np.ones((morphological_kernel, morphological_kernel), np.uint8)
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections: List[Detection] = []
    for c in contours:
        area = int(cv2.contourArea(c))
        if area < min_contour_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = float(M["m10"] / M["m00"])  # type: ignore[call-overload]
            cy = float(M["m01"] / M["m00"])  # type: ignore[call-overload]
        else:
            cx, cy = float(x + w / 2.0), float(y + h / 2.0)
        # mean magnitude within bbox
        roi = diff[y : y + h, x : x + w]
        magnitude = float(np.mean(roi)) if roi.size else 0.0
        detections.append(Detection(bbox=(x, y, w, h), area=area, centroid=(cx, cy), magnitude=magnitude))

    logger.info("Detected %d candidate changes", len(detections))
    return detections

