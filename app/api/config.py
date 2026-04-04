import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.threshold import ThresholdConfig

logger = logging.getLogger("locomotive")

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
    summary="Get all threshold configs",
    description="Returns all threshold configurations.",
)
async def get_thresholds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ThresholdConfig))
    rows = result.scalars().all()
    return {
        "data": [
            ThresholdResponse.model_validate(r).model_dump(by_alias=True)
            for r in rows
        ]
    }


@router.put(
    "/thresholds",
    summary="Update threshold config",
    description="Updates one parameter's thresholds.",
)
async def update_threshold(
    body: ThresholdUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ThresholdConfig).where(ThresholdConfig.parameter == body.parameter)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail=f"Parameter '{body.parameter}' not found")

    config.warning_value = body.warning_value
    config.critical_value = body.critical_value
    await db.commit()
    await db.refresh(config)
    logger.info("Updated threshold for %s: warning=%.2f, critical=%.2f", body.parameter, body.warning_value, body.critical_value)

    return ThresholdResponse.model_validate(config).model_dump(by_alias=True)
