import random
import time

from app.schemas.telemetry import TelemetrySnapshotSchema, TelemetryPosition
from app.utils.math import clamp

INITIAL_STATE = {
    "speed": 80,
    "temperature": 72,
    "oil_temperature": 85,
    "vibration": 2.1,
    "voltage": 25.0,
    "current": 420,
    "fuel_level": 87,
    "fuel_consumption": 180,
    "brake_pressure": 0.55,
    "traction_effort": 220,
    "efficiency": 88,
    "lat": 43.238,
    "lng": 76.946,
}


def drift(range_val: float) -> float:
    return (random.random() - 0.5) * range_val


class SimulatorState:
    def __init__(self) -> None:
        self.speed = INITIAL_STATE["speed"]
        self.temperature = INITIAL_STATE["temperature"]
        self.oil_temperature = INITIAL_STATE["oil_temperature"]
        self.vibration = INITIAL_STATE["vibration"]
        self.voltage = INITIAL_STATE["voltage"]
        self.current = INITIAL_STATE["current"]
        self.fuel_level = INITIAL_STATE["fuel_level"]
        self.fuel_consumption = INITIAL_STATE["fuel_consumption"]
        self.brake_pressure = INITIAL_STATE["brake_pressure"]
        self.traction_effort = INITIAL_STATE["traction_effort"]
        self.efficiency = INITIAL_STATE["efficiency"]
        self.lat = INITIAL_STATE["lat"]
        self.lng = INITIAL_STATE["lng"]

    def next_tick(self) -> TelemetrySnapshotSchema:
        self.speed = clamp(self.speed + drift(8), 0, 200)
        self.temperature = clamp(
            self.temperature + drift(2) + (0.3 if self.speed > 120 else -0.1),
            40, 120,
        )
        self.oil_temperature = clamp(self.oil_temperature + drift(1.5), 60, 150)
        self.vibration = clamp(self.vibration + drift(0.5), 0.5, 10)
        self.voltage = clamp(self.voltage + drift(0.3), 20, 30)
        self.current = clamp(self.current + drift(30), 100, 1000)
        self.fuel_level = clamp(self.fuel_level - random.random() * 0.05, 0, 100)
        self.fuel_consumption = clamp(self.fuel_consumption + drift(15), 80, 500)
        self.brake_pressure = clamp(self.brake_pressure + drift(0.03), 0.1, 1.0)
        self.traction_effort = clamp(self.speed * 2.5 + drift(20), 0, 500)
        self.efficiency = clamp(self.efficiency + drift(2), 40, 100)

        lat_step = 0.002 * (random.random() * 0.5 + 0.5)
        lng_step = -0.001 * (random.random() * 0.5 + 0.5)
        self.lat += lat_step
        self.lng += lng_step

        timestamp = int(time.time() * 1000)

        return TelemetrySnapshotSchema(
            timestamp=timestamp,
            speed=self.speed,
            temperature=self.temperature,
            oil_temperature=self.oil_temperature,
            vibration=self.vibration,
            voltage=self.voltage,
            current=self.current,
            fuel_level=self.fuel_level,
            fuel_consumption=self.fuel_consumption,
            brake_pressure=self.brake_pressure,
            traction_effort=self.traction_effort,
            efficiency=self.efficiency,
            position=TelemetryPosition(lat=self.lat, lng=self.lng),
        )
