from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

_pool_kwargs: dict = (
    {"pool_size": 10, "max_overflow": 20, "pool_timeout": 30, "pool_recycle": 1800}
    if settings.is_production
    else {"pool_size": 5, "max_overflow": 10}
)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    **_pool_kwargs,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
