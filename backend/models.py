from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, Text, DateTime, func


class Base(DeclarativeBase):
    pass


class FAQ(Base):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string opcional
    lang: Mapped[str] = mapped_column(Text, nullable=False, default="es")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )