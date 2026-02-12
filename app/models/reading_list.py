import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReadingList(Base):
    __tablename__ = "reading_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    discussion_prompts: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_reading_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    items: Mapped[list["ReadingListItem"]] = relationship(
        back_populates="reading_list", cascade="all, delete-orphan"
    )


class ReadingListItem(Base):
    __tablename__ = "reading_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reading_list_id: Mapped[int] = mapped_column(
        ForeignKey("reading_lists.id"), nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id"), nullable=False
    )
    section: Mapped[str] = mapped_column(String(256), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reading_list: Mapped["ReadingList"] = relationship(back_populates="items")
    article = relationship("Article")
