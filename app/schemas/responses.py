from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.schemas.alert import AlertSchema
from app.schemas.recommendation import Recommendation
from app.schemas.telemetry import TelemetrySnapshotSchema


class HealthCheckResponse(BaseModel):
    status: str
    db: str
    simulator: str
    scenario: str
    clients: int


class ScenarioInfo(BaseModel):
    id: str
    name: str
    description: str


class ScenarioListResponse(BaseModel):
    scenarios: list[ScenarioInfo]


class ScenarioResponse(BaseModel):
    scenario: str
    message: str


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str


class ScenarioErrorResponse(BaseModel):
    error: str


class AlertListResponse(BaseModel):
    data: list[dict]


class HistoryResponse(BaseModel):
    data: list[dict]


class RecommendationListResponse(BaseModel):
    data: list[dict]


class ThresholdListResponse(BaseModel):
    data: list[dict]
