import pytest

from app.services.simulator import SimulatorState, INITIAL_STATE


def test_initial_state_has_correct_values(simulator_state):
    assert simulator_state.speed == INITIAL_STATE["speed"]
    assert simulator_state.temperature == INITIAL_STATE["temperature"]
    assert simulator_state.fuel_level == INITIAL_STATE["fuel_level"]
    assert simulator_state.voltage == INITIAL_STATE["voltage"]
    assert simulator_state.brake_pressure == INITIAL_STATE["brake_pressure"]


def test_tick_produces_values_within_ranges(simulator_state):
    snapshot = simulator_state.next_tick()
    assert 0 <= snapshot.speed <= 200
    assert 40 <= snapshot.temperature <= 120
    assert 60 <= snapshot.oil_temperature <= 150
    assert 0.5 <= snapshot.vibration <= 10
    assert 20 <= snapshot.voltage <= 30
    assert 100 <= snapshot.current <= 1000
    assert 0 <= snapshot.fuel_level <= 100
    assert 80 <= snapshot.fuel_consumption <= 500
    assert 0.1 <= snapshot.brake_pressure <= 1.0
    assert 0 <= snapshot.traction_effort <= 500
    assert 40 <= snapshot.efficiency <= 100


def test_overheat_scenario_increases_temperature():
    state = SimulatorState(scenario="overheat")
    initial_temp = state.temperature
    # Run several ticks to see trend
    temps = []
    for _ in range(20):
        snapshot = state.next_tick()
        temps.append(snapshot.temperature)
    # Average of later temps should be higher than initial
    avg_later = sum(temps[10:]) / len(temps[10:])
    assert avg_later > initial_temp


def test_100_ticks_stay_within_bounds(simulator_state):
    for _ in range(100):
        snapshot = simulator_state.next_tick()
        assert 0 <= snapshot.speed <= 200
        assert 40 <= snapshot.temperature <= 120
        assert 60 <= snapshot.oil_temperature <= 150
        assert 0.5 <= snapshot.vibration <= 10
        assert 20 <= snapshot.voltage <= 30
        assert 100 <= snapshot.current <= 1000
        assert 0 <= snapshot.fuel_level <= 100
        assert 80 <= snapshot.fuel_consumption <= 500
        assert 0.1 <= snapshot.brake_pressure <= 1.0
        assert 0 <= snapshot.traction_effort <= 500
        assert 40 <= snapshot.efficiency <= 100


def test_tick_count_increments(simulator_state):
    assert simulator_state.tick_count == 0
    simulator_state.next_tick()
    assert simulator_state.tick_count == 1
    simulator_state.next_tick()
    assert simulator_state.tick_count == 2


def test_scenario_switch():
    state = SimulatorState(scenario="normal")
    state.next_tick()
    state.scenario = "overheat"
    state.tick_count = 0
    snapshot = state.next_tick()
    assert snapshot is not None
    assert state.tick_count == 1
