from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AlertSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    timestamp: int
    severity: str
    message: str
    parameter: str
    value: float
    threshold: float
    error_code: str | None = None
