from datetime import datetime

from sqlalchemy import String, Double, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class ThresholdConfig(Base):
    __tablename__ = "threshold_config"

    parameter: Mapped[str] = mapped_column(String(50), primary_key=True)
    min_value: Mapped[float] = mapped_column(Double, nullable=False)
    max_value: Mapped[float] = mapped_column(Double, nullable=False)
    warning_value: Mapped[float] = mapped_column(Double, nullable=False)
    critical_value: Mapped[float] = mapped_column(Double, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
