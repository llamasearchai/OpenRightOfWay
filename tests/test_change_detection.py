from pathlib import Path

import cv2
import numpy as np

from openrightofway.cv.change_detection import detect_changes


def test_detect_changes(tmp_path: Path):
    # create simple before/after images
    before = np.zeros((100, 100, 3), dtype=np.uint8)
    after = before.copy()
    cv2.rectangle(after, (30, 30), (70, 70), (255, 255, 255), -1)

    before_path = tmp_path / "before.png"
    after_path = tmp_path / "after.png"
    cv2.imwrite(str(before_path), before)
    cv2.imwrite(str(after_path), after)

    dets = detect_changes(str(before_path), str(after_path), change_threshold=10, min_contour_area=50)
    assert len(dets) >= 1
    assert all(d.area > 0 for d in dets)

