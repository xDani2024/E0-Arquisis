from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from master.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    idpk: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    package_body: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )