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
    def __init__(self, scenario: str = "normal") -> None:
        self.scenario = scenario
        self.tick_count = 0

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

    def _apply_scenario_bias(self) -> dict[str, float]:
        """Returns additive biases per parameter based on active scenario."""
        bias: dict[str, float] = {}

        if self.scenario == "overheat":
            # Temperature climbs steadily, oil follows, efficiency drops
            bias["temperature"] = 0.8
            bias["oil_temperature"] = 0.5
            bias["vibration"] = 0.1
            bias["efficiency"] = -0.3

        elif self.scenario == "brake_failure":
            # Brake pressure drops steadily, vibration rises
            bias["brake_pressure"] = -0.008
            bias["vibration"] = 0.15

        elif self.scenario == "low_fuel":
            # Fuel drops 10x faster than normal
            bias["fuel_level"] = -0.4
            bias["efficiency"] = -0.2

        elif self.scenario == "highload":
            # Speed up, everything stressed
            bias["speed"] = 2.0
            bias["temperature"] = 0.5
            bias["current"] = 15
            bias["vibration"] = 0.08
            bias["fuel_consumption"] = 5

        elif self.scenario == "demo":
            # Cycles through phases to show variety during a live demo
            # Phase 1 (0-30s): normal cruise
            # Phase 2 (30-60s): overheat developing
            # Phase 3 (60-90s): brake pressure dropping
            # Phase 4 (90-120s): recovery back to normal
            # Then repeats
            phase = (self.tick_count % 120)
            if phase < 30:
                pass  # normal
            elif phase < 60:
                bias["temperature"] = 1.0
                bias["oil_temperature"] = 0.6
                bias["vibration"] = 0.12
                bias["efficiency"] = -0.4
            elif phase < 90:
                bias["brake_pressure"] = -0.01
                bias["vibration"] = 0.15
                bias["voltage"] = -0.08
            else:
                # Recovery: push values back toward normal
                bias["temperature"] = -0.6
                bias["oil_temperature"] = -0.4
                bias["brake_pressure"] = 0.008
                bias["vibration"] = -0.1
                bias["voltage"] = 0.05
                bias["efficiency"] = 0.3

        return bias

    def next_tick(self) -> TelemetrySnapshotSchema:
        self.tick_count += 1
        bias = self._apply_scenario_bias()

        self.speed = clamp(
            self.speed + drift(8) + bias.get("speed", 0),
            0, 200,
        )
        self.temperature = clamp(
            self.temperature + drift(2) + (0.3 if self.speed > 120 else -0.1) + bias.get("temperature", 0),
            40, 120,
        )
        self.oil_temperature = clamp(
            self.oil_temperature + drift(1.5) + bias.get("oil_temperature", 0),
            60, 150,
        )
        self.vibration = clamp(
            self.vibration + drift(0.5) + bias.get("vibration", 0),
            0.5, 10,
        )
        self.voltage = clamp(
            self.voltage + drift(0.3) + bias.get("voltage", 0),
            20, 30,
        )
        self.current = clamp(
            self.current + drift(30) + bias.get("current", 0),
            100, 1000,
        )
        self.fuel_level = clamp(
            self.fuel_level - random.random() * 0.05 + bias.get("fuel_level", 0),
            0, 100,
        )
        self.fuel_consumption = clamp(
            self.fuel_consumption + drift(15) + bias.get("fuel_consumption", 0),
            80, 500,
        )
        self.brake_pressure = clamp(
            self.brake_pressure + drift(0.03) + bias.get("brake_pressure", 0),
            0.1, 1.0,
        )
        self.traction_effort = clamp(self.speed * 2.5 + drift(20), 0, 500)
        self.efficiency = clamp(
            self.efficiency + drift(2) + bias.get("efficiency", 0),
            40, 100,
        )

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
