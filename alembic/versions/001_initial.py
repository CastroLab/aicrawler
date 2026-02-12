"""Initial schema with FTS5

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Articles
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source", sa.String(256), server_default=""),
        sa.Column("published_date", sa.Date, nullable=True),
        sa.Column("content_type", sa.String(64), server_default="article"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("key_findings", sa.Text, nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=True),
        sa.Column("word_count", sa.Integer, nullable=True),
        sa.Column("reading_time_minutes", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_articles_url_hash", "articles", ["url_hash"])
    op.create_index("ix_articles_status", "articles", ["status"])

    # Article authors
    op.create_table(
        "article_authors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("article_id", sa.Integer, sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
    )

    # Tags
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(64), server_default="topic"),
        sa.UniqueConstraint("name", "category", name="uq_tag_name_cat"),
    )

    # Article-Tag junction
    op.create_table(
        "article_tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("article_id", sa.Integer, sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id"), nullable=False),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.UniqueConstraint("article_id", "tag_id", name="uq_article_tag"),
    )

    # Search jobs
    op.create_table(
        "search_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("schedule", sa.String(64), server_default="daily"),
        sa.Column("enabled", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Search executions
    op.create_table(
        "search_executions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("search_job_id", sa.Integer, sa.ForeignKey("search_jobs.id"), nullable=False),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(32), server_default="running"),
        sa.Column("articles_found", sa.Integer, server_default="0"),
        sa.Column("articles_new", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(256), server_default=""),
        sa.Column("role", sa.String(32), server_default="member"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Reading lists
    op.create_table(
        "reading_lists",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("query", sa.Text, nullable=True),
        sa.Column("discussion_prompts", sa.Text, nullable=True),
        sa.Column("total_reading_time", sa.Integer, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Reading list items
    op.create_table(
        "reading_list_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("reading_list_id", sa.Integer, sa.ForeignKey("reading_lists.id"), nullable=False),
        sa.Column("article_id", sa.Integer, sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("section", sa.String(256), server_default=""),
        sa.Column("position", sa.Integer, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # Interrogation log
    op.create_table(
        "interrogation_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("query_plan", sa.Text, nullable=True),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("reading_list_id", sa.Integer, sa.ForeignKey("reading_lists.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # FTS5 virtual table + triggers
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title, summary, content='articles', content_rowid='id'
        )
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(rowid, title, summary)
            VALUES (new.id, new.title, COALESCE(new.summary, ''));
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, summary)
            VALUES ('delete', old.id, old.title, COALESCE(old.summary, ''));
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, summary)
            VALUES ('delete', old.id, old.title, COALESCE(old.summary, ''));
            INSERT INTO articles_fts(rowid, title, summary)
            VALUES (new.id, new.title, COALESCE(new.summary, ''));
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS articles_au")
    op.execute("DROP TRIGGER IF EXISTS articles_ad")
    op.execute("DROP TRIGGER IF EXISTS articles_ai")
    op.execute("DROP TABLE IF EXISTS articles_fts")
    op.drop_table("interrogation_log")
    op.drop_table("reading_list_items")
    op.drop_table("reading_lists")
    op.drop_table("search_executions")
    op.drop_table("search_jobs")
    op.drop_table("article_tags")
    op.drop_table("tags")
    op.drop_table("article_authors")
    op.drop_table("users")
    op.drop_table("articles")
