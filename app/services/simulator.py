import random
import time

from app.schemas.telemetry import TelemetrySnapshotSchema, TelemetryPosition
from app.services.routes import RouteManager, RouteTickResult
from app.utils.math import clamp

STATION_KEY = {
    "Кульсары": "qulsary",
    "Актау": "aqtau",
    "Алматы": "almaty",
    "Астана": "astana",
}


def _resolve_background_key(result: RouteTickResult, train_state: str) -> str:
    current_key = STATION_KEY.get(result.current_station_name, "qulsary")
    next_key = STATION_KEY.get(result.next_station_name or "", current_key)

    if result.completed or train_state == "stopped":
        return f"{current_key}-image"
    if train_state == "approaching_station":
        return f"{next_key}-approaching"
    return f"{current_key}-moving"

# KZ8A Electric Locomotive characteristics
# Max speed: 120 km/h, sustained speed: 52 km/h, cruising: ~75-80 km/h
# Power: 8×1100 kW = 8800 kW, Mass: 200 t, AC 25 kV
# Traction motors: 8× asynchronous, 1072.5 kW each (sustained)

CRUISING_SPEED = 78.0       # typical freight cruising speed (km/h)
MAX_SPEED = 120.0           # construction max
ACCEL_TICKS = 3             # ticks to reach cruising speed from standstill
MEAN_REVERSION = 0.15       # how strongly speed returns to cruising target

INITIAL_STATE = {
    "speed": 0,
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

        self.route_manager = RouteManager()
        self.route_completed = False
        self._ticks_since_depart = 0  # ticks since leaving a station
        self._was_at_station = True   # start at station

    def reset_to_defaults(self) -> None:
        """Reset all telemetry values to safe initial state."""
        for key, value in INITIAL_STATE.items():
            setattr(self, key, value)
        self.route_manager = RouteManager()
        self.route_completed = False
        self._ticks_since_depart = 0
        self._was_at_station = True

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
            # Phase 1 (0-40s): normal cruise — health A
            # Phase 2 (40-55s): mild stress — health dips to B
            # Phase 3 (55-70s): moderate stress — health dips to B/C
            # Phase 4 (70-100s): recovery back to A
            # Repeats every 100s
            phase = (self.tick_count % 100)
            if phase < 40:
                # Normal — gently push back to safe values
                if self.temperature > 80:
                    bias["temperature"] = -1.0
                if self.oil_temperature > 90:
                    bias["oil_temperature"] = -0.5
                if self.brake_pressure < 0.5:
                    bias["brake_pressure"] = 0.015
                if self.vibration > 3:
                    bias["vibration"] = -0.1
                if self.efficiency < 85:
                    bias["efficiency"] = 0.5
            elif phase < 55:
                # Mild overheat — warning level, not critical
                bias["temperature"] = 0.8
                bias["oil_temperature"] = 0.5
                bias["vibration"] = 0.08
                bias["efficiency"] = -0.3
            elif phase < 70:
                # Moderate brake stress — warning level
                bias["brake_pressure"] = -0.008
                bias["vibration"] = 0.1
                bias["voltage"] = -0.05
            else:
                # Recovery — pull everything back to normal
                bias["temperature"] = -1.5
                bias["oil_temperature"] = -0.8
                bias["brake_pressure"] = 0.02
                bias["vibration"] = -0.15
                bias["voltage"] = 0.08
                bias["efficiency"] = 0.6

        return bias

    def next_tick(self) -> TelemetrySnapshotSchema:
        self.tick_count += 1
        bias = self._apply_scenario_bias()

        # Speed: acceleration after station stop, then mean-reversion to cruising
        ticks_moving = self._ticks_since_depart
        if ticks_moving <= ACCEL_TICKS:
            # Ramp up from 0 to cruising speed over ACCEL_TICKS
            target = CRUISING_SPEED * (ticks_moving / ACCEL_TICKS)
            self.speed = clamp(target + drift(3), 0, MAX_SPEED)
        else:
            # Mean-revert toward cruising speed + scenario bias + small noise
            speed_target = CRUISING_SPEED + bias.get("speed", 0)
            reversion = (speed_target - self.speed) * MEAN_REVERSION
            self.speed = clamp(
                self.speed + reversion + drift(3),
                0, MAX_SPEED,
            )
        self.temperature = clamp(
            self.temperature + drift(2) + (0.3 if self.speed > 100 else -0.1) + bias.get("temperature", 0),
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
        # Current proportional to power: P = V × I, at 25kV
        # Cruising ~350A, accelerating ~500A, idle ~100A
        target_current = 100 + self.speed * 4.5
        self.current = clamp(
            self.current + (target_current - self.current) * 0.1 + drift(15) + bias.get("current", 0),
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
        # KZ8A: max traction ~450 kN at low speed, decreasing with speed
        base_traction = max(0, 450 - self.speed * 2.5) if self.speed > 0 else 0
        self.traction_effort = clamp(base_traction + drift(15), 0, 500)
        self.efficiency = clamp(
            self.efficiency + drift(2) + bias.get("efficiency", 0),
            40, 100,
        )

        # Advance along the active route
        train_state = "moving"
        route_result: RouteTickResult | None = None
        if not self.route_completed:
            route_result = self.route_manager.tick()
            self.lat = route_result.lat
            self.lng = route_result.lng

            if route_result.at_station:
                train_state = "stopped"
                # At station — idle values
                self.speed = 0
                self.traction_effort = 0
                self.fuel_consumption = clamp(85 + drift(5), 80, 100)
                self.current = clamp(110 + drift(10), 100, 130)
                self.vibration = clamp(0.3 + drift(0.1), 0.2, 0.5)
                self.brake_pressure = clamp(0.85 + drift(0.02), 0.8, 0.9)
                self.efficiency = 0
                self.temperature = clamp(self.temperature - 0.5, 50, 120)
                self.oil_temperature = clamp(self.oil_temperature - 0.3, 65, 150)
                self._was_at_station = True
                self._ticks_since_depart = 0

                if route_result.completed:
                    self.route_completed = True
            elif route_result.approaching_station:
                train_state = "approaching_station"
                if self._was_at_station:
                    self._was_at_station = False
                    self._ticks_since_depart = 0
                self._ticks_since_depart += 1
            else:
                train_state = "moving"
                if self._was_at_station:
                    self._was_at_station = False
                    self._ticks_since_depart = 0
                self._ticks_since_depart += 1
        else:
            train_state = "stopped"

        # Resolve background key
        if route_result is not None:
            background_key = _resolve_background_key(route_result, train_state)
        else:
            background_key = "astana-image"  # route completed, at final station

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
            train_state=train_state,
            background_key=background_key,
        )
