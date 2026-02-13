import logging

from sqlalchemy.orm import Session

from app.clients.claude import call_claude_structured
from app.models.article import Article
from app.models.content import ArticleContent
from app.models.tag import ArticleTag, Tag
from app.services.reading_time import estimate_reading_time

logger = logging.getLogger(__name__)

# Maximum words to include from full text in the prompt (~12K words)
MAX_CONTENT_WORDS = 12000

ENRICHMENT_SCHEMA = {
    "type": "object",
    "required": [
        "summary", "key_findings", "tags", "relevance_score",
        "content_type", "word_count",
    ],
    "properties": {
        "summary": {
            "type": "string",
            "description": (
                "2-3 paragraph executive summary leading with 'so what' — why should "
                "an AI working group at a higher education institution care about this? "
                "What are the institutional implications?"
            ),
        },
        "key_findings": {
            "type": "string",
            "description": (
                "Bullet-point list of actionable findings focused on institutional "
                "implications. Each bullet should help a committee member understand "
                "what this means for their college or university."
            ),
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "category", "confidence"],
                "properties": {
                    "name": {"type": "string", "description": "Tag name, lowercase"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "topic", "stance", "methodology", "policy_area",
                            "sector", "urgency",
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
        "relevance_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": (
                "How relevant is this to an AI working group at a higher education "
                "institution? Scoring guide: 0.7-1.0 = potential agenda item (directly "
                "impacts institutional AI policy, teaching, or operations), 0.4-0.7 = "
                "useful background (broader trends that inform the group's work), "
                "0.0-0.4 = tangential (interesting but not actionable for the group)"
            ),
        },
        "content_type": {
            "type": "string",
            "enum": [
                "article", "paper", "report", "blog_post",
                "policy_document", "news", "other",
            ],
        },
        "word_count": {
            "type": "integer",
            "description": "Estimated word count of the full article",
        },
    },
}

SYSTEM_PROMPT = """You are a research analyst supporting an AI working group at a \
higher education institution. The working group includes faculty, administrators, and \
IT leaders who need to stay informed about AI developments that affect their institution.

Your job is to produce executive-level summaries that help the committee understand:
- What happened and why it matters to higher education
- Institutional implications (policy, teaching, research, operations, student experience)
- Whether and how the working group should respond

Scope of interest (in priority order):
1. AI policy in higher education (primary focus)
2. Broader ed tech trends affecting colleges and universities
3. K-12 AI developments that will impact incoming students
4. Workforce/employer AI expectations that affect curriculum
5. Government AI regulation that may constrain or enable institutions

Tag categories:
- topic: subject matter (e.g., "academic integrity", "generative ai", "assessment", "curriculum")
- stance: perspective (e.g., "pro-regulation", "cautious optimism", "critical", "neutral")
- methodology: research approach (e.g., "qualitative study", "policy analysis", "opinion", "survey")
- policy_area: institutional domain (e.g., "teaching", "research", "administration", "student services")
- sector: where it applies (e.g., "higher_ed", "k12", "workforce", "government", "industry")
- urgency: time-sensitivity (e.g., "breaking", "emerging", "established")

Lead with the "so what" — committee members are busy and need to know quickly whether \
this matters and what to do about it."""

USER_PROMPT_WITH_CONTENT = """Article to analyze:
Title: {title}
URL: {url}
Source: {source}
Content Type: {content_type}
Published: {published_date}

--- Full Article Text ---
{full_text}
--- End Article Text ---

Analyze this article and provide the structured enrichment. You have the full article \
text above, so your summary should be substantive and specific, not generic."""

USER_PROMPT_METADATA_ONLY = """Article to analyze:
Title: {title}
URL: {url}
Source: {source}
Content Type: {content_type}
Published: {published_date}

NOTE: Full article text is not available (the article may be behind a paywall or \
could not be fetched). Provide your best analysis based on the title, source, and URL. \
Be transparent that your analysis is based on metadata only — flag this limitation in \
your summary. Estimate word count based on typical articles from this source."""


def _truncate_text(text: str, max_words: int = MAX_CONTENT_WORDS) -> str:
    """Truncate text to approximately max_words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "\n\n[... truncated for length]"


def enrich_article(db: Session, article: Article) -> bool:
    """Enrich a single article with AI-generated metadata. Returns True on success."""
    # Determine if we have content
    content_record = (
        db.query(ArticleContent)
        .filter(ArticleContent.article_id == article.id)
        .first()
    )
    has_full_text = (
        content_record
        and content_record.fetch_status in ("success", "partial")
        and content_record.full_text
    )

    if has_full_text:
        user_prompt = USER_PROMPT_WITH_CONTENT.format(
            title=article.title,
            url=article.url,
            source=article.source,
            content_type=article.content_type,
            published_date=article.published_date or "Unknown",
            full_text=_truncate_text(content_record.full_text),
        )
    else:
        user_prompt = USER_PROMPT_METADATA_ONLY.format(
            title=article.title,
            url=article.url,
            source=article.source,
            content_type=article.content_type,
            published_date=article.published_date or "Unknown",
        )

    result = call_claude_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=ENRICHMENT_SCHEMA,
    )

    if not result:
        article.status = "error"
        db.commit()
        return False

    article.summary = result["summary"]
    article.key_findings = result["key_findings"]
    article.relevance_score = result["relevance_score"]
    article.content_type = result["content_type"]
    article.status = "enriched"

    # Use real word count from content if available, otherwise Claude's estimate
    if has_full_text and content_record.word_count:
        article.word_count = content_record.word_count
    else:
        article.word_count = result["word_count"]
    article.reading_time_minutes = estimate_reading_time(article.word_count)

    # Get-or-create tags
    for tag_data in result.get("tags", []):
        tag = (
            db.query(Tag)
            .filter(Tag.name == tag_data["name"], Tag.category == tag_data["category"])
            .first()
        )
        if not tag:
            tag = Tag(name=tag_data["name"], category=tag_data["category"])
            db.add(tag)
            db.flush()

        existing_link = (
            db.query(ArticleTag)
            .filter(ArticleTag.article_id == article.id, ArticleTag.tag_id == tag.id)
            .first()
        )
        if not existing_link:
            db.add(
                ArticleTag(
                    article_id=article.id,
                    tag_id=tag.id,
                    confidence=tag_data.get("confidence", 1.0),
                )
            )

    db.commit()
    logger.info("Enriched article %d: %s", article.id, article.title)
    return True


def enrich_pending_articles(db: Session, batch_size: int = 10) -> dict:
    """Enrich articles that are ready for enrichment. Returns summary stats.

    Picks up both 'fetched' and 'fetch_failed' articles (not just 'pending'),
    since fetch_failed articles can still be enriched from metadata.
    """
    articles = (
        db.query(Article)
        .filter(Article.status.in_(["fetched", "fetch_failed"]))
        .order_by(Article.created_at)
        .limit(batch_size)
        .all()
    )

    stats = {"total": len(articles), "success": 0, "error": 0}
    for article in articles:
        if enrich_article(db, article):
            stats["success"] += 1
        else:
            stats["error"] += 1

    logger.info("Enrichment batch: %s", stats)
    return stats
