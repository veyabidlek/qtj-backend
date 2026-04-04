from app.schemas.health import HealthIndex, HealthBreakdown, HealthFactor
from app.schemas.telemetry import TelemetrySnapshotSchema


def score_param(
    value: float,
    min_val: float,
    max_val: float,
    warning: float,
    critical: float,
    invert: bool,
) -> float:
    if invert:
        if value <= critical:
            return 10.0
        if value <= warning:
            return 40.0 + ((value - critical) / (warning - critical)) * 30.0
        return 70.0 + ((value - warning) / (max_val - warning)) * 30.0
    else:
        if value >= critical:
            return 10.0
        if value >= warning:
            return 40.0 + ((critical - value) / (critical - warning)) * 30.0
        return 70.0 + ((warning - value) / (warning - min_val)) * 30.0


def get_grade(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "E"


def get_status(score: int) -> str:
    if score >= 80:
        return "Норма"
    if score >= 50:
        return "Внимание"
    return "Критично"


def compute_health(snapshot: TelemetrySnapshotSchema) -> HealthIndex:
    # Engine subsystem
    engine_temp = score_param(snapshot.temperature, 0, 120, 95, 105, invert=False)
    oil_temp = score_param(snapshot.oil_temperature, 0, 150, 110, 130, invert=False)
    vib = score_param(snapshot.vibration, 0, 10, 5, 7, invert=False)
    engine_score = (engine_temp + oil_temp + vib) / 3.0

    # Electrical subsystem
    volt = score_param(snapshot.voltage, 20, 30, 22, 21, invert=True)
    curr = score_param(snapshot.current, 0, 1000, 800, 900, invert=False)
    eff = score_param(100 - snapshot.efficiency, 0, 100, 40, 60, invert=False)
    electrical_score = (volt + curr + eff) / 3.0

    # Brakes subsystem
    brake = score_param(1 - snapshot.brake_pressure, 0, 1, 0.7, 0.85, invert=False)
    brakes_score = brake

    # Fuel subsystem
    fuel = score_param(100 - snapshot.fuel_level, 0, 100, 75, 90, invert=False)
    fuel_score = fuel

    breakdown = HealthBreakdown(
        engine=round(engine_score),
        electrical=round(electrical_score),
        brakes=round(brakes_score),
        fuel=round(fuel_score),
    )

    score = round(
        breakdown.engine * 0.30
        + breakdown.electrical * 0.25
        + breakdown.brakes * 0.25
        + breakdown.fuel * 0.20
    )

    factors = [
        HealthFactor(parameter="Двигатель", impact=breakdown.engine, status=get_status(breakdown.engine)),
        HealthFactor(parameter="Электрика", impact=breakdown.electrical, status=get_status(breakdown.electrical)),
        HealthFactor(parameter="Тормоза", impact=breakdown.brakes, status=get_status(breakdown.brakes)),
        HealthFactor(parameter="Топливо", impact=breakdown.fuel, status=get_status(breakdown.fuel)),
    ]
    factors.sort(key=lambda f: f.impact)

    return HealthIndex(
        score=score,
        grade=get_grade(score),
        breakdown=breakdown,
        top_factors=factors,
    )
