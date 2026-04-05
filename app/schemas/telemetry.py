from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TelemetryPosition(BaseModel):
    lat: float
    lng: float


class TelemetrySnapshotSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    timestamp: int
    speed: float
    temperature: float
    oil_temperature: float
    vibration: float
    voltage: float
    current: float
    fuel_level: float
    fuel_consumption: float
    brake_pressure: float
    traction_effort: float
    efficiency: float
    position: TelemetryPosition
    train_state: str = "moving"  # "stopped", "moving", "approaching_station"
