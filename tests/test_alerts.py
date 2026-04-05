import pytest

from app.services.alerts import check_alerts, DEFAULT_THRESHOLDS
from app.schemas.telemetry import TelemetrySnapshotSchema, TelemetryPosition


def test_no_alerts_normal_values(normal_snapshot):
    alerts = check_alerts(normal_snapshot)
    assert len(alerts) == 0


def test_temperature_above_warning_generates_warning():
    snapshot = TelemetrySnapshotSchema(
        timestamp=1700000000000,
        speed=80,
        temperature=98,  # above warning (95) but below critical (105)
        oil_temperature=85,
        vibration=2.1,
        voltage=25.0,
        current=420,
        fuel_level=87,
        fuel_consumption=180,
        brake_pressure=0.55,
        traction_effort=220,
        efficiency=88,
        position=TelemetryPosition(lat=43.238, lng=76.946),
    )
    alerts = check_alerts(snapshot)
    temp_alerts = [a for a in alerts if a.parameter == "temperature"]
    assert len(temp_alerts) == 1
    assert temp_alerts[0].severity == "warning"
    assert temp_alerts[0].error_code == "E-101"


def test_fuel_level_below_critical_generates_critical():
    snapshot = TelemetrySnapshotSchema(
        timestamp=1700000000000,
        speed=80,
        temperature=72,
        oil_temperature=85,
        vibration=2.1,
        voltage=25.0,
        current=420,
        fuel_level=8,  # below critical (10)
        fuel_consumption=180,
        brake_pressure=0.55,
        traction_effort=220,
        efficiency=88,
        position=TelemetryPosition(lat=43.238, lng=76.946),
    )
    alerts = check_alerts(snapshot)
    fuel_alerts = [a for a in alerts if a.parameter == "fuel_level"]
    assert len(fuel_alerts) == 1
    assert fuel_alerts[0].severity == "critical"
    assert fuel_alerts[0].error_code == "E-401"


def test_multiple_simultaneous_alerts(all_critical_snapshot):
    alerts = check_alerts(all_critical_snapshot)
    assert len(alerts) >= 3  # Multiple parameters should trigger
    parameters = {a.parameter for a in alerts}
    assert "temperature" in parameters
    assert "speed" in parameters


def test_custom_thresholds_override_defaults():
    snapshot = TelemetrySnapshotSchema(
        timestamp=1700000000000,
        speed=80,
        temperature=72,
        oil_temperature=85,
        vibration=2.1,
        voltage=25.0,
        current=420,
        fuel_level=87,
        fuel_consumption=180,
        brake_pressure=0.55,
        traction_effort=220,
        efficiency=88,
        position=TelemetryPosition(lat=43.238, lng=76.946),
    )
    # With default thresholds, speed=80 should not alert
    alerts = check_alerts(snapshot)
    assert len(alerts) == 0

    # With custom thresholds where speed warning is 70, speed=80 should alert
    custom = dict(DEFAULT_THRESHOLDS)
    custom["speed"] = {"warning": 70, "critical": 90}
    alerts = check_alerts(snapshot, custom)
    speed_alerts = [a for a in alerts if a.parameter == "speed"]
    assert len(speed_alerts) == 1
    assert speed_alerts[0].severity == "warning"


def test_all_11_parameters_checked():
    """Verify all 11 parameters are covered in the alert checks."""
    expected = {
        "speed", "temperature", "oil_temperature", "vibration",
        "voltage", "current", "fuel_level", "fuel_consumption",
        "brake_pressure", "traction_effort", "efficiency",
    }
    from app.services.alerts import ALERT_CHECKS
    actual = {check["key"] for check in ALERT_CHECKS}
    assert actual == expected
