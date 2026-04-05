import logging

from app.schemas.alert import AlertSchema
from app.schemas.telemetry import TelemetrySnapshotSchema

logger = logging.getLogger("locomotive")

ERROR_CODES: dict[str, dict[str, str]] = {
    "temperature": {"code": "E-101", "description": "Перегрев двигателя"},
    "oil_temperature": {"code": "E-102", "description": "Перегрев масла"},
    "vibration": {"code": "E-201", "description": "Критическая вибрация"},
    "voltage": {"code": "E-301", "description": "Отклонение напряжения"},
    "current": {"code": "E-302", "description": "Перегрузка по току"},
    "efficiency": {"code": "E-303", "description": "Низкий КПД"},
    "fuel_level": {"code": "E-401", "description": "Низкий уровень топлива"},
    "fuel_consumption": {"code": "E-402", "description": "Аномальный расход"},
    "brake_pressure": {"code": "E-501", "description": "Низкое давление тормозов"},
    "speed": {"code": "E-601", "description": "Превышение скорости"},
    "traction_effort": {"code": "E-602", "description": "Перегрузка тяги"},
}

# Parameters that alert when value goes ABOVE the threshold
ABOVE_PARAMS = {"speed", "temperature", "oil_temperature", "vibration", "current", "fuel_consumption", "traction_effort"}
# Parameters that alert when value goes BELOW the threshold
BELOW_PARAMS = {"voltage", "fuel_level", "brake_pressure", "efficiency"}

ALERT_CHECKS = [
    {"key": "speed", "label": "Скорость"},
    {"key": "temperature", "label": "Температура двигателя"},
    {"key": "oil_temperature", "label": "Температура масла"},
    {"key": "vibration", "label": "Вибрация"},
    {"key": "voltage", "label": "Напряжение"},
    {"key": "current", "label": "Ток"},
    {"key": "fuel_level", "label": "Уровень топлива"},
    {"key": "fuel_consumption", "label": "Расход топлива"},
    {"key": "brake_pressure", "label": "Давление тормозов"},
    {"key": "traction_effort", "label": "Тяговое усилие"},
    {"key": "efficiency", "label": "КПД"},
]

DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "speed": {"warning": 160, "critical": 180},
    "temperature": {"warning": 95, "critical": 105},
    "oil_temperature": {"warning": 110, "critical": 130},
    "vibration": {"warning": 5, "critical": 7},
    "voltage": {"warning": 22, "critical": 21},
    "current": {"warning": 800, "critical": 900},
    "fuel_level": {"warning": 25, "critical": 10},
    "fuel_consumption": {"warning": 350, "critical": 420},
    "brake_pressure": {"warning": 0.3, "critical": 0.15},
    "traction_effort": {"warning": 400, "critical": 450},
    "efficiency": {"warning": 60, "critical": 40},
}


def check_alerts(
    snapshot: TelemetrySnapshotSchema,
    thresholds: dict[str, dict[str, float]] | None = None,
) -> list[AlertSchema]:
    alerts: list[AlertSchema] = []
    timestamp = snapshot.timestamp
    effective_thresholds = thresholds if thresholds else DEFAULT_THRESHOLDS

    for check in ALERT_CHECKS:
        key = check["key"]
        if key not in effective_thresholds:
            continue

        value = getattr(snapshot, key)
        threshold = effective_thresholds[key]
        error_code_info = ERROR_CODES.get(key)
        error_code = error_code_info["code"] if error_code_info else None
        inverted = key in BELOW_PARAMS

        if inverted:
            if value <= threshold["critical"]:
                severity = "critical"
                message = f"{check['label']}: критически низкое значение"
                triggered_threshold = threshold["critical"]
            elif value <= threshold["warning"]:
                severity = "warning"
                message = f"{check['label']}: требует внимания"
                triggered_threshold = threshold["warning"]
            else:
                continue
        else:
            if value >= threshold["critical"]:
                severity = "critical"
                message = f"{check['label']}: критически высокое значение"
                triggered_threshold = threshold["critical"]
            elif value >= threshold["warning"]:
                severity = "warning"
                message = f"{check['label']}: требует внимания"
                triggered_threshold = threshold["warning"]
            else:
                continue

        alert = AlertSchema(
            id=f"{key}-{timestamp}",
            timestamp=timestamp,
            severity=severity,
            message=message,
            parameter=key,
            value=value,
            threshold=triggered_threshold,
            error_code=error_code,
        )
        alerts.append(alert)
        logger.warning("Alert: %s — %s (value=%.2f, threshold=%.2f)", severity, message, value, triggered_threshold)

    return alerts
