import datetime as dt

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SearchJob(Base):
    __tablename__ = "search_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    schedule: Mapped[str] = mapped_column(String(64), default="daily")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    executions: Mapped[list["SearchExecution"]] = relationship(
        back_populates="search_job", cascade="all, delete-orphan"
    )


class SearchExecution(Base):
    __tablename__ = "search_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    articles_found: Mapped[int] = mapped_column(Integer, default=0)
    articles_new: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    from sqlalchemy import ForeignKey

    search_job_id: Mapped[int] = mapped_column(
        ForeignKey("search_jobs.id"), nullable=False
    )

    search_job: Mapped["SearchJob"] = relationship(back_populates="executions")
