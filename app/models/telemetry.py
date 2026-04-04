from sqlalchemy import BigInteger, DateTime, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class TelemetrySnapshot(Base):
    __tablename__ = "telemetry_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    speed: Mapped[float] = mapped_column(Double, nullable=False)
    temperature: Mapped[float] = mapped_column(Double, nullable=False)
    oil_temperature: Mapped[float] = mapped_column(Double, nullable=False)
    vibration: Mapped[float] = mapped_column(Double, nullable=False)
    voltage: Mapped[float] = mapped_column(Double, nullable=False)
    current_amperage: Mapped[float] = mapped_column(Double, nullable=False)
    fuel_level: Mapped[float] = mapped_column(Double, nullable=False)
    fuel_consumption: Mapped[float] = mapped_column(Double, nullable=False)
    brake_pressure: Mapped[float] = mapped_column(Double, nullable=False)
    traction_effort: Mapped[float] = mapped_column(Double, nullable=False)
    efficiency: Mapped[float] = mapped_column(Double, nullable=False)
    lat: Mapped[float] = mapped_column(Double, nullable=False)
    lng: Mapped[float] = mapped_column(Double, nullable=False)

    __table_args__ = (
        Index("idx_telemetry_ts", "timestamp", postgresql_using="btree"),
    )
