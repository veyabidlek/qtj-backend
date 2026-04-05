from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.threshold import ThresholdConfig


async def get_all_thresholds(session: AsyncSession) -> list[ThresholdConfig]:
    result = await session.execute(select(ThresholdConfig))
    return list(result.scalars().all())


async def get_threshold(session: AsyncSession, parameter: str) -> ThresholdConfig | None:
    result = await session.execute(
        select(ThresholdConfig).where(ThresholdConfig.parameter == parameter)
    )
    return result.scalar_one_or_none()


async def update_threshold(
    session: AsyncSession,
    parameter: str,
    warning: float,
    critical: float,
) -> ThresholdConfig | None:
    config = await get_threshold(session, parameter)
    if config is None:
        return None
    config.warning_value = warning
    config.critical_value = critical
    await session.commit()
    await session.refresh(config)
    return config


async def seed_thresholds(session: AsyncSession, data: list[dict]) -> None:
    result = await session.execute(select(func.count()).select_from(ThresholdConfig))
    count = result.scalar()
    if count and count > 0:
        return
    for row in data:
        session.add(ThresholdConfig(**row))
    await session.commit()
