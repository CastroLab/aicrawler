"""Content fetching and digest system

Revision ID: 002
Revises: 001
Create Date: 2025-02-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add has_content column to articles
    op.add_column("articles", sa.Column("has_content", sa.Boolean, server_default="0"))

    # Article content table
    op.create_table(
        "article_content",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("article_id", sa.Integer, sa.ForeignKey("articles.id"), nullable=False, unique=True),
        sa.Column("full_text", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("fetch_status", sa.String(32), server_default="pending"),
        sa.Column("fetch_error", sa.Text, nullable=True),
        sa.Column("http_status", sa.Integer, nullable=True),
        sa.Column("extracted_title", sa.String(512), nullable=True),
        sa.Column("extracted_author", sa.String(512), nullable=True),
        sa.Column("extracted_date", sa.String(64), nullable=True),
        sa.Column("word_count", sa.Integer, nullable=True),
        sa.Column("fetched_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Digests table
    op.create_table(
        "digests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("digest_type", sa.String(32), server_default="manual"),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("period_start", sa.DateTime, nullable=True),
        sa.Column("period_end", sa.DateTime, nullable=True),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("trend_analysis", sa.Text, nullable=True),
        sa.Column("full_markdown", sa.Text, nullable=True),
        sa.Column("article_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Digest sections table
    op.create_table(
        "digest_sections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("digest_id", sa.Integer, sa.ForeignKey("digests.id"), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("section_type", sa.String(32), server_default="theme"),
        sa.Column("content_markdown", sa.Text, nullable=True),
        sa.Column("position", sa.Integer, server_default="0"),
    )

    # Digest articles junction table
    op.create_table(
        "digest_articles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("section_id", sa.Integer, sa.ForeignKey("digest_sections.id"), nullable=False),
        sa.Column("article_id", sa.Integer, sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("highlight_note", sa.Text, nullable=True),
        sa.Column("position", sa.Integer, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("digest_articles")
    op.drop_table("digest_sections")
    op.drop_table("digests")
    op.drop_table("article_content")
    op.drop_column("articles", "has_content")
