import os

import yaml

from app.core.logging import get_logger
from app.schemas.health import HealthIndex, HealthBreakdown, HealthFactor
from app.schemas.telemetry import TelemetrySnapshotSchema

logger = get_logger("locomotive.health")

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "health_config.yaml")

_config: dict | None = None


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def get_config() -> dict:
    global _config
    if _config is None:
        _config = _load_config()
    return _config


def reload_config() -> dict:
    global _config
    _config = _load_config()
    logger.info("health_config_reloaded", path=_CONFIG_PATH)
    return _config


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
    cfg = get_config()
    grades = cfg.get("grades", {})
    # Sort grades by min descending to find the first match
    for grade_letter in sorted(grades, key=lambda g: grades[g]["min"], reverse=True):
        if score >= grades[grade_letter]["min"]:
            return grade_letter
    return "E"


def get_status(score: int) -> str:
    if score >= 80:
        return "Норма"
    if score >= 50:
        return "Внимание"
    return "Критично"


def compute_health(snapshot: TelemetrySnapshotSchema) -> HealthIndex:
    cfg = get_config()
    weights = cfg["weights"]

    # Engine subsystem
    engine_temp = score_param(snapshot.temperature, 0, 120, 95, 105, invert=False)
    oil_temp = score_param(snapshot.oil_temperature, 0, 150, 110, 130, invert=False)
    vib = score_param(snapshot.vibration, 0, 10, 5, 7, invert=False)

    params = cfg["parameters"]
    engine_score = (
        engine_temp * params["temperature"]["weight_in_group"]
        + oil_temp * params["oil_temperature"]["weight_in_group"]
        + vib * params["vibration"]["weight_in_group"]
    )

    # Electrical subsystem
    volt = score_param(snapshot.voltage, 20, 30, 22, 21, invert=True)
    curr = score_param(snapshot.current, 0, 1000, 800, 900, invert=False)
    eff = score_param(100 - snapshot.efficiency, 0, 100, 40, 60, invert=False)
    electrical_score = (
        volt * params["voltage"]["weight_in_group"]
        + curr * params["current"]["weight_in_group"]
        + eff * params["efficiency"]["weight_in_group"]
    )

    # Brakes subsystem
    brake = score_param(1 - snapshot.brake_pressure, 0, 1, 0.7, 0.85, invert=False)
    brakes_score = brake * params["brake_pressure"]["weight_in_group"]

    # Fuel subsystem
    fuel = score_param(100 - snapshot.fuel_level, 0, 100, 75, 90, invert=False)
    fuel_score = fuel * params["fuel_level"]["weight_in_group"]

    breakdown = HealthBreakdown(
        engine=round(engine_score),
        electrical=round(electrical_score),
        brakes=round(brakes_score),
        fuel=round(fuel_score),
    )

    score = round(
        breakdown.engine * weights["engine"]
        + breakdown.electrical * weights["electrical"]
        + breakdown.brakes * weights["brakes"]
        + breakdown.fuel * weights["fuel"]
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
