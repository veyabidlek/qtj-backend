from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class HealthBreakdown(BaseModel):
    engine: int
    electrical: int
    brakes: int
    fuel: int


class HealthFactor(BaseModel):
    parameter: str
    impact: int
    status: str


class HealthIndex(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    score: int
    grade: str
    breakdown: HealthBreakdown
    top_factors: list[HealthFactor]
