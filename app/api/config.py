from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import verify_api_key
from app.repositories import health_config_repo
from app.schemas.responses import ThresholdListResponse

logger = get_logger("locomotive.config")

router = APIRouter(prefix="/api/config", tags=["config"])


class ThresholdResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    parameter: str
    min_value: float
    max_value: float
    warning_value: float
    critical_value: float


class ThresholdUpdateRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    parameter: str
    warning_value: float
    critical_value: float


@router.get(
    "/thresholds",
    response_model=ThresholdListResponse,
    summary="Get all threshold configs",
    description="Returns all threshold configurations.",
)
async def get_thresholds(db: AsyncSession = Depends(get_db)):
    rows = await health_config_repo.get_all_thresholds(db)
    return {
        "data": [
            ThresholdResponse.model_validate(r).model_dump(by_alias=True)
            for r in rows
        ]
    }


@router.put(
    "/thresholds",
    response_model=ThresholdResponse,
    summary="Update threshold config",
    description="Updates one parameter's thresholds.",
)
async def update_threshold(
    body: ThresholdUpdateRequest,
    _api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    config = await health_config_repo.update_threshold(
        db, body.parameter, body.warning_value, body.critical_value
    )
    if config is None:
        raise HTTPException(status_code=404, detail=f"Parameter '{body.parameter}' not found")

    logger.info("threshold_updated", parameter=body.parameter, warning=body.warning_value, critical=body.critical_value)
    return ThresholdResponse.model_validate(config)
