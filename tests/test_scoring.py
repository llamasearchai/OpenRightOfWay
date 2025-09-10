from openrightofway.scoring.threat import compute_threat


def test_scoring_distance_effect():
    close = compute_threat(encroachment_type="structure", distance_m=5.0, compliance_ok=False, magnitude=200.0, area_pixels=2000)
    far = compute_threat(encroachment_type="structure", distance_m=100.0, compliance_ok=False, magnitude=200.0, area_pixels=2000)
    assert close.score > far.score

