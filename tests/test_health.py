import pytest

from app.services.health import compute_health, get_grade
from app.schemas.telemetry import TelemetrySnapshotSchema, TelemetryPosition


def test_normal_params_high_score(normal_snapshot):
    health = compute_health(normal_snapshot)
    assert health.score >= 85
    assert health.grade == "A"


def test_single_critical_param_drops_score(critical_temperature_snapshot):
    health = compute_health(critical_temperature_snapshot)
    # Score should drop below 100 but not be catastrophic
    assert health.score < 90
    # The top factor (lowest impact) should be engine-related
    assert health.top_factors[0].parameter == "Двигатель"


def test_all_critical_low_grade(all_critical_snapshot):
    health = compute_health(all_critical_snapshot)
    assert health.grade in ("D", "E")
    assert health.score < 40


def test_grade_boundary_80_is_A():
    assert get_grade(80) == "A"


def test_grade_boundary_79_is_B():
    assert get_grade(79) == "B"


def test_grade_boundary_60_is_B():
    assert get_grade(60) == "B"


def test_grade_boundary_59_is_C():
    assert get_grade(59) == "C"


def test_grade_boundary_40_is_C():
    assert get_grade(40) == "C"


def test_grade_boundary_39_is_D():
    assert get_grade(39) == "D"


def test_grade_boundary_20_is_D():
    assert get_grade(20) == "D"


def test_grade_boundary_19_is_E():
    assert get_grade(19) == "E"


def test_grade_boundary_0_is_E():
    assert get_grade(0) == "E"


def test_breakdown_has_all_subsystems(normal_snapshot):
    health = compute_health(normal_snapshot)
    assert hasattr(health.breakdown, "engine")
    assert hasattr(health.breakdown, "electrical")
    assert hasattr(health.breakdown, "brakes")
    assert hasattr(health.breakdown, "fuel")
