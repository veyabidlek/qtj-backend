import pytest

from app.schemas.telemetry import TelemetrySnapshotSchema, TelemetryPosition
from app.services.simulator import SimulatorState, INITIAL_STATE


@pytest.fixture
def normal_snapshot() -> TelemetrySnapshotSchema:
    """A snapshot with all parameters in normal/safe ranges."""
    return TelemetrySnapshotSchema(
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


@pytest.fixture
def critical_temperature_snapshot() -> TelemetrySnapshotSchema:
    """A snapshot with critical temperature (110 > critical 105)."""
    return TelemetrySnapshotSchema(
        timestamp=1700000001000,
        speed=80,
        temperature=110,
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


@pytest.fixture
def all_critical_snapshot() -> TelemetrySnapshotSchema:
    """A snapshot with many parameters in critical ranges."""
    return TelemetrySnapshotSchema(
        timestamp=1700000002000,
        speed=185,
        temperature=115,
        oil_temperature=140,
        vibration=8.5,
        voltage=20.5,
        current=950,
        fuel_level=5,
        fuel_consumption=450,
        brake_pressure=0.12,
        traction_effort=460,
        efficiency=35,
        position=TelemetryPosition(lat=43.238, lng=76.946),
    )


@pytest.fixture
def simulator_state() -> SimulatorState:
    return SimulatorState(scenario="normal")
