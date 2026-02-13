import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ArticleContent(Base):
    __tablename__ = "article_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id"), unique=True, nullable=False
    )

    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    fetch_status: Mapped[str] = mapped_column(String(32), default="pending")
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)

    extracted_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    extracted_author: Mapped[str | None] = mapped_column(String(512), nullable=True)
    extracted_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    fetched_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    article: Mapped["Article"] = relationship(back_populates="content")

    def __repr__(self) -> str:
        return f"<ArticleContent article_id={self.article_id} status={self.fetch_status}>"
