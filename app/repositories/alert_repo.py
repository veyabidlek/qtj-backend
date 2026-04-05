from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


async def insert_alert(session: AsyncSession, alert_data: dict) -> None:
    session.add(Alert(**alert_data))


async def get_alerts(
    session: AsyncSession,
    severity: str | None = None,
    limit: int = 50,
) -> list[Alert]:
    query = select(Alert).order_by(Alert.timestamp.desc())
    if severity:
        query = query.where(Alert.severity == severity)
    query = query.limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def delete_old(session: AsyncSession, hours: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    await session.execute(
        delete(Alert).where(Alert.timestamp < cutoff)
    )
    await session.commit()
