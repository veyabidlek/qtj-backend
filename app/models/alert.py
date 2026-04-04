from sqlalchemy import DateTime, String, Double, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from sqlalchemy.sql import func

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    parameter: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Double, nullable=False)
    threshold: Mapped[float] = mapped_column(Double, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    __table_args__ = (
        Index("idx_alerts_ts", "timestamp", postgresql_using="btree"),
        Index("idx_alerts_severity", "severity"),
    )
