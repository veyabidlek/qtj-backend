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
    "fuel_level": {"code": "E-401", "description": "Низкий уровень топлива"},
    "fuel_consumption": {"code": "E-402", "description": "Аномальный расход"},
    "brake_pressure": {"code": "E-501", "description": "Низкое давление тормозов"},
    "speed": {"code": "E-601", "description": "Превышение скорости"},
    "traction_effort": {"code": "E-701", "description": "Перегрузка тяги"},
    "efficiency": {"code": "E-801", "description": "Низкий КПД"},
}

ALERT_CHECKS = [
    {"key": "temperature", "label": "Температура двигателя", "inverted": False},
    {"key": "vibration", "label": "Вибрация", "inverted": False},
    {"key": "voltage", "label": "Напряжение", "inverted": True},
    {"key": "fuel_level", "label": "Уровень топлива", "inverted": True},
    {"key": "speed", "label": "Скорость", "inverted": False},
]

THRESHOLDS: dict[str, dict[str, float]] = {
    "speed": {"warning": 160, "critical": 180},
    "temperature": {"warning": 95, "critical": 105},
    "vibration": {"warning": 5, "critical": 7},
    "voltage": {"warning": 22, "critical": 21},
    "fuel_level": {"warning": 25, "critical": 10},
}


def check_alerts(snapshot: TelemetrySnapshotSchema) -> list[AlertSchema]:
    alerts: list[AlertSchema] = []
    timestamp = snapshot.timestamp

    for check in ALERT_CHECKS:
        value = getattr(snapshot, check["key"])
        threshold = THRESHOLDS[check["key"]]
        error_code_info = ERROR_CODES.get(check["key"])
        error_code = error_code_info["code"] if error_code_info else None

        if check["inverted"]:
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
            id=f"{check['key']}-{timestamp}",
            timestamp=timestamp,
            severity=severity,
            message=message,
            parameter=check["key"],
            value=value,
            threshold=triggered_threshold,
            error_code=error_code,
        )
        alerts.append(alert)
        logger.warning("Alert: %s — %s (value=%.2f, threshold=%.2f)", severity, message, value, triggered_threshold)

    return alerts
