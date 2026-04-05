import random
import time

from app.schemas.telemetry import TelemetrySnapshotSchema, TelemetryPosition
from app.utils.math import clamp

ASTANA_ALMATY_ROUTE = [
    (51.1694, 71.4491),   # Astana
    (50.9983, 71.3654),   # South of Astana
    (50.5954, 71.1128),   # Karagandy region
    (50.2839, 70.9536),
    (49.8028, 70.4567),
    (49.2101, 69.9345),
    (48.6733, 69.4012),
    (48.0195, 68.8234),
    (47.4536, 68.3456),
    (46.8467, 67.7892),
    (46.3012, 67.2345),
    (45.7234, 66.8901),
    (45.0123, 76.1234),   # Approaching Almaty region
    (44.5192, 76.5678),
    (43.9012, 76.8234),
    (43.4853, 76.8901),
    (43.2380, 76.9460),   # Almaty
]

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
    "lat": 51.1694,
    "lng": 71.4491,
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
        self.route_progress = 0.0
        self._route_direction = 1  # 1 = forward, -1 = reverse

    def _apply_scenario_bias(self) -> dict[str, float]:
        """Returns additive biases per parameter based on active scenario."""
        bias: dict[str, float] = {}

        if self.scenario == "overheat":
            bias["temperature"] = 2.0
            bias["oil_temperature"] = 1.5
            bias["vibration"] = 0.2
            bias["efficiency"] = -0.8

        elif self.scenario == "brake_failure":
            bias["brake_pressure"] = -0.02
            bias["vibration"] = 0.2

        elif self.scenario == "low_fuel":
            bias["fuel_level"] = -1.0
            bias["efficiency"] = -0.5

        elif self.scenario == "highload":
            bias["speed"] = 4.0
            bias["temperature"] = 1.5
            bias["current"] = 25
            bias["vibration"] = 0.15
            bias["fuel_consumption"] = 10

        elif self.scenario == "demo":
            # Phase 1 (0-20s): normal cruise
            # Phase 2 (20-50s): overheat — alerts within ~15s
            # Phase 3 (50-80s): brake failure — alerts within ~15s
            # Phase 4 (80-100s): recovery
            # Repeats every 100s
            phase = (self.tick_count % 100)
            if phase < 20:
                # Normal — gently push back to safe values
                if self.temperature > 80:
                    bias["temperature"] = -1.5
                if self.brake_pressure < 0.4:
                    bias["brake_pressure"] = 0.02
                if self.vibration > 3:
                    bias["vibration"] = -0.15
            elif phase < 50:
                # Overheat phase
                bias["temperature"] = 2.0
                bias["oil_temperature"] = 1.2
                bias["vibration"] = 0.2
                bias["efficiency"] = -0.8
            elif phase < 80:
                # Brake failure phase
                bias["brake_pressure"] = -0.02
                bias["vibration"] = 0.2
                bias["voltage"] = -0.15
            else:
                # Recovery
                bias["temperature"] = -2.0
                bias["oil_temperature"] = -1.0
                bias["brake_pressure"] = 0.03
                bias["vibration"] = -0.2
                bias["voltage"] = 0.1
                bias["efficiency"] = 0.8

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

        # Advance along the Astana-Almaty route
        self.route_progress += self._route_direction * 0.002
        if self.route_progress >= 1.0:
            self.route_progress = 1.0
            self._route_direction = -1
        elif self.route_progress <= 0.0:
            self.route_progress = 0.0
            self._route_direction = 1

        num_segments = len(ASTANA_ALMATY_ROUTE) - 1
        scaled = self.route_progress * num_segments
        idx = min(int(scaled), num_segments - 1)
        frac = scaled - idx
        lat1, lng1 = ASTANA_ALMATY_ROUTE[idx]
        lat2, lng2 = ASTANA_ALMATY_ROUTE[idx + 1]
        self.lat = lat1 + (lat2 - lat1) * frac
        self.lng = lng1 + (lng2 - lng1) * frac

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
