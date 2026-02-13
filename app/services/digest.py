import datetime as dt
import json
import logging

from sqlalchemy.orm import Session, joinedload

from app.clients.claude import call_claude_structured
from app.models.article import Article
from app.models.content import ArticleContent
from app.models.digest import Digest, DigestArticle, DigestSection
from app.models.tag import ArticleTag

logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_DIGEST = 50

DIGEST_SCHEMA = {
    "type": "object",
    "required": [
        "title", "executive_summary", "trend_analysis",
        "sections", "discussion_questions", "action_items",
    ],
    "properties": {
        "title": {
            "type": "string",
            "description": "Briefing title, e.g. 'AI Working Group Briefing: Feb 3-9, 2025'",
        },
        "executive_summary": {
            "type": "string",
            "description": (
                "3-5 paragraph executive summary of the most important developments. "
                "Lead with what's new or changing. Focus on institutional implications."
            ),
        },
        "trend_analysis": {
            "type": "string",
            "description": (
                "2-3 paragraphs on emerging patterns, shifts in the landscape, or "
                "evolving themes across the articles in this period."
            ),
        },
        "sections": {
            "type": "array",
            "description": "Thematic groupings of articles (not chronological)",
            "items": {
                "type": "object",
                "required": ["title", "narrative", "article_ids", "article_highlights"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Thematic section heading",
                    },
                    "narrative": {
                        "type": "string",
                        "description": (
                            "2-4 paragraph narrative tying together the articles in this "
                            "section. Professional but accessible tone."
                        ),
                    },
                    "article_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "IDs of articles in this section",
                    },
                    "article_highlights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "One-line highlight per article (same order as article_ids)",
                    },
                },
            },
        },
        "discussion_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-5 discussion questions for the working group meeting",
        },
        "action_items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-4 suggested action items for the working group",
        },
    },
}

DIGEST_SYSTEM_PROMPT = """You are a research analyst preparing a periodic briefing for \
an AI working group at a higher education institution. The working group includes \
faculty, administrators, and IT leaders.

Your briefing should be:
- Professional but accessible (no jargon without explanation)
- Thematically organized (NOT chronological)
- Focused on what's NEW or CHANGING in this period
- Connected to institutional implications (policy, teaching, research, operations)
- Actionable — every section should help the group decide what to discuss or do

Structure the briefing with:
1. An executive summary that a busy dean could read in 2 minutes
2. Thematic sections grouping related articles with narrative synthesis
3. Trend analysis connecting dots across the period
4. Discussion questions for the next meeting
5. Suggested action items

When grouping articles into sections, think about what themes will resonate with \
committee members: regulatory changes, academic integrity, student AI use, institutional \
strategy, workforce preparation, etc."""


def _gather_articles(
    db: Session,
    period_start: dt.datetime,
    period_end: dt.datetime,
    max_articles: int = MAX_ARTICLES_PER_DIGEST,
) -> list[Article]:
    """Gather enriched articles for the digest period, sorted by relevance."""
    articles = (
        db.query(Article)
        .options(
            joinedload(Article.authors),
            joinedload(Article.article_tags).joinedload(ArticleTag.tag),
        )
        .filter(
            Article.status == "enriched",
            Article.created_at >= period_start,
            Article.created_at <= period_end,
        )
        .order_by(Article.relevance_score.desc().nullslast())
        .limit(max_articles)
        .all()
    )
    # Deduplicate from joinedload
    seen = set()
    unique = []
    for a in articles:
        if a.id not in seen:
            seen.add(a.id)
            unique.append(a)
    return unique


def _build_article_summaries(articles: list[Article]) -> str:
    """Build a text block summarizing articles for the Claude prompt."""
    parts = []
    for a in articles:
        tags = ", ".join(
            f"{at.tag.name} ({at.tag.category})"
            for at in a.article_tags
            if at.tag
        )
        parts.append(
            f"[Article ID: {a.id}]\n"
            f"Title: {a.title}\n"
            f"Source: {a.source}\n"
            f"Published: {a.published_date or 'Unknown'}\n"
            f"Relevance: {a.relevance_score or 'N/A'}\n"
            f"Tags: {tags or 'None'}\n"
            f"Summary: {a.summary or 'No summary available'}\n"
            f"Key Findings: {a.key_findings or 'None'}\n"
        )
    return "\n---\n".join(parts)


def _render_markdown(digest: Digest) -> str:
    """Render a complete digest as polished Markdown."""
    lines = []
    lines.append(f"# {digest.title}")
    lines.append("")

    if digest.period_start and digest.period_end:
        start = digest.period_start.strftime("%B %d, %Y")
        end = digest.period_end.strftime("%B %d, %Y")
        lines.append(f"**Period:** {start} — {end}")
        lines.append(f"**Articles reviewed:** {digest.article_count}")
        lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(digest.executive_summary or "")
    lines.append("")

    for section in digest.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(section.content_markdown or "")
        lines.append("")

        if section.articles:
            lines.append("**Sources:**")
            for da in section.articles:
                if da.article:
                    highlight = f" — {da.highlight_note}" if da.highlight_note else ""
                    lines.append(f"- [{da.article.title}]({da.article.url}){highlight}")
            lines.append("")

    if digest.trend_analysis:
        lines.append("## Trend Analysis")
        lines.append("")
        lines.append(digest.trend_analysis)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by AICrawler*")
    return "\n".join(lines)


def generate_digest(
    db: Session,
    period_start: dt.datetime,
    period_end: dt.datetime,
    digest_type: str = "manual",
) -> Digest | None:
    """Generate a digest for the given time period."""
    # Create digest record
    digest = Digest(
        title=f"AI Working Group Briefing",
        digest_type=digest_type,
        status="generating",
        period_start=period_start,
        period_end=period_end,
    )
    db.add(digest)
    db.commit()

    try:
        # Phase 1: Gather articles
        articles = _gather_articles(db, period_start, period_end)
        if not articles:
            digest.status = "error"
            digest.executive_summary = "No enriched articles found for this period."
            db.commit()
            return digest

        digest.article_count = len(articles)

        # Phase 2: Synthesize with Claude
        article_text = _build_article_summaries(articles)
        start_str = period_start.strftime("%B %d, %Y")
        end_str = period_end.strftime("%B %d, %Y")

        user_prompt = f"""Generate a briefing for the AI working group covering \
{start_str} to {end_str}.

There are {len(articles)} articles to review. Here they are:

{article_text}

Organize these into a cohesive briefing. Use the article IDs when referencing articles \
in your sections. Every article_id you reference must be from the list above."""

        result = call_claude_structured(
            system_prompt=DIGEST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=DIGEST_SCHEMA,
            max_tokens=8192,
        )

        if not result:
            digest.status = "error"
            digest.executive_summary = "AI synthesis failed."
            db.commit()
            return digest

        # Store results
        digest.title = result["title"]
        digest.executive_summary = result["executive_summary"]
        digest.trend_analysis = result["trend_analysis"]

        # Create article ID lookup
        article_map = {a.id: a for a in articles}

        # Create sections
        for pos, section_data in enumerate(result.get("sections", [])):
            section = DigestSection(
                digest_id=digest.id,
                title=section_data["title"],
                section_type="theme",
                content_markdown=section_data["narrative"],
                position=pos,
            )
            db.add(section)
            db.flush()

            # Link articles to section
            highlights = section_data.get("article_highlights", [])
            for idx, art_id in enumerate(section_data.get("article_ids", [])):
                if art_id in article_map:
                    highlight = highlights[idx] if idx < len(highlights) else None
                    db.add(DigestArticle(
                        section_id=section.id,
                        article_id=art_id,
                        highlight_note=highlight,
                        position=idx,
                    ))

        # Add discussion questions as a section
        questions = result.get("discussion_questions", [])
        if questions:
            q_markdown = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
            db.add(DigestSection(
                digest_id=digest.id,
                title="Discussion Questions",
                section_type="recommendation",
                content_markdown=q_markdown,
                position=len(result.get("sections", [])),
            ))

        # Add action items as a section
        actions = result.get("action_items", [])
        if actions:
            a_markdown = "\n".join(f"- {a}" for a in actions)
            db.add(DigestSection(
                digest_id=digest.id,
                title="Suggested Action Items",
                section_type="recommendation",
                content_markdown=a_markdown,
                position=len(result.get("sections", [])) + 1,
            ))

        digest.status = "completed"
        db.commit()

        # Refresh to load sections for markdown rendering
        db.refresh(digest)
        digest.full_markdown = _render_markdown(digest)
        db.commit()

        logger.info("Generated digest %d: %s (%d articles)", digest.id, digest.title, digest.article_count)
        return digest

    except Exception:
        logger.exception("Digest generation failed for digest %d", digest.id)
        digest.status = "error"
        db.commit()
        return digest


def generate_weekly_digest(db: Session) -> Digest | None:
    """Generate a weekly digest covering the past 7 days."""
    now = dt.datetime.now(dt.timezone.utc)
    period_end = now
    period_start = now - dt.timedelta(days=7)
    return generate_digest(db, period_start, period_end, digest_type="weekly")
