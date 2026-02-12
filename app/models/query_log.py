import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InterrogationLog(Base):
    __tablename__ = "interrogation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    reading_list_id: Mapped[int | None] = mapped_column(
        ForeignKey("reading_lists.id"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
