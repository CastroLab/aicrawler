import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    digest_type: Mapped[str] = mapped_column(String(32), default="manual")
    status: Mapped[str] = mapped_column(String(32), default="pending")

    period_start: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    trend_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    article_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    sections: Mapped[list["DigestSection"]] = relationship(
        back_populates="digest", cascade="all, delete-orphan",
        order_by="DigestSection.position",
    )

    def __repr__(self) -> str:
        return f"<Digest {self.id}: {self.title[:50]}>"


class DigestSection(Base):
    __tablename__ = "digest_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_id: Mapped[int] = mapped_column(
        ForeignKey("digests.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    section_type: Mapped[str] = mapped_column(String(32), default="theme")
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    digest: Mapped["Digest"] = relationship(back_populates="sections")
    articles: Mapped[list["DigestArticle"]] = relationship(
        back_populates="section", cascade="all, delete-orphan",
        order_by="DigestArticle.position",
    )

    def __repr__(self) -> str:
        return f"<DigestSection {self.id}: {self.title[:40]}>"


class DigestArticle(Base):
    __tablename__ = "digest_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("digest_sections.id"), nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id"), nullable=False
    )
    highlight_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    section: Mapped["DigestSection"] = relationship(back_populates="articles")
    article: Mapped["Article"] = relationship()

    def __repr__(self) -> str:
        return f"<DigestArticle section={self.section_id} article={self.article_id}>"
