from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(
        String(64), default="topic"
    )  # topic, stance, methodology, policy_area

    article_tags: Mapped[list["ArticleTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("name", "category", name="uq_tag_name_cat"),)


class ArticleTag(Base):
    __tablename__ = "article_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    article = relationship("Article", back_populates="article_tags")
    tag: Mapped["Tag"] = relationship(back_populates="article_tags")

    __table_args__ = (
        UniqueConstraint("article_id", "tag_id", name="uq_article_tag"),
    )
