from app.schemas.recommendation import Recommendation
from app.schemas.telemetry import TelemetrySnapshotSchema
from app.schemas.health import HealthIndex


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def get_recommendations(
    snapshot: TelemetrySnapshotSchema,
    health: HealthIndex,
) -> list[Recommendation]:
    results: list[Recommendation] = []

    rules = [
        {
            "id": "temperature",
            "parameter": "temperature",
            "check": lambda s, h: s.temperature > 95,
            "priority": "high",
            "title": "Снизить нагрузку на двигатель",
            "description": "Температура двигателя выше 95°C. Рекомендуется снизить тяговое усилие и контролировать охлаждение.",
        },
        {
            "id": "fuelLevel",
            "parameter": "fuelLevel",
            "check": lambda s, h: s.fuel_level < 25,
            "priority": "high",
            "title": "Запланировать дозаправку",
            "description": "Уровень топлива ниже 25%. Запланируйте остановку на ближайшей станции с депо.",
        },
        {
            "id": "vibration",
            "parameter": "vibration",
            "check": lambda s, h: s.vibration > 5,
            "priority": "high",
            "title": "Диагностика вибрации",
            "description": "Повышенная вибрация может указывать на износ подшипников или дисбаланс. Рекомендуется осмотр.",
        },
        {
            "id": "brakePressure",
            "parameter": "brakePressure",
            "check": lambda s, h: s.brake_pressure < 0.3,
            "priority": "high",
            "title": "Проверить тормозную систему",
            "description": "Давление в тормозной магистрали ниже нормы. Возможна утечка или неисправность компрессора.",
        },
        {
            "id": "voltage",
            "parameter": "voltage",
            "check": lambda s, h: s.voltage < 22.5,
            "priority": "medium",
            "title": "Проверить генератор",
            "description": "Напряжение ниже оптимального диапазона. Проверьте состояние генератора и контактной сети.",
        },
        {
            "id": "efficiency",
            "parameter": "efficiency",
            "check": lambda s, h: s.efficiency < 60,
            "priority": "medium",
            "title": "Оптимизировать режим работы",
            "description": "КПД ниже 60%. Проверьте режим тяги и состояние электрических цепей.",
        },
        {
            "id": "oilTemperature",
            "parameter": "oilTemperature",
            "check": lambda s, h: s.oil_temperature > 110,
            "priority": "medium",
            "title": "Контроль температуры масла",
            "description": "Температура масла выше нормы. Проверьте уровень и состояние масла, работу маслоохладителя.",
        },
        {
            "id": "health",
            "parameter": "health",
            "check": lambda s, h: h.score < 50,
            "priority": "high",
            "title": "Требуется техническое обслуживание",
            "description": "Общий индекс здоровья ниже 50. Рекомендуется внеплановая диагностика на ближайшей станции.",
        },
    ]

    for rule in rules:
        if rule["check"](snapshot, health):
            results.append(
                Recommendation(
                    id=rule["id"],
                    priority=rule["priority"],
                    title=rule["title"],
                    description=rule["description"],
                    parameter=rule["parameter"],
                )
            )

    results.sort(key=lambda r: PRIORITY_ORDER.get(r.priority, 2))
    return results
