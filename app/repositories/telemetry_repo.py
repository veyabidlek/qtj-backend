from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import TelemetrySnapshot


async def insert_batch(session: AsyncSession, snapshots: list[dict]) -> None:
    for row in snapshots:
        session.add(TelemetrySnapshot(**row))
    await session.commit()


async def get_history(session: AsyncSession, minutes: int) -> list[TelemetrySnapshot]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    result = await session.execute(
        select(TelemetrySnapshot)
        .where(TelemetrySnapshot.timestamp >= cutoff)
        .order_by(TelemetrySnapshot.timestamp.asc())
    )
    return list(result.scalars().all())


async def delete_old(session: AsyncSession, hours: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    await session.execute(
        delete(TelemetrySnapshot).where(TelemetrySnapshot.timestamp < cutoff)
    )
    await session.commit()


async def export_history(session: AsyncSession, minutes: int) -> list[TelemetrySnapshot]:
    return await get_history(session, minutes)
