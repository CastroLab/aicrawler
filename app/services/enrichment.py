import logging

from sqlalchemy.orm import Session

from app.clients.claude import call_claude_structured
from app.models.article import Article
from app.models.tag import ArticleTag, Tag
from app.services.reading_time import estimate_reading_time

logger = logging.getLogger(__name__)

ENRICHMENT_SCHEMA = {
    "type": "object",
    "required": ["summary", "key_findings", "tags", "relevance_score", "content_type", "word_count"],
    "properties": {
        "summary": {
            "type": "string",
            "description": "2-3 paragraph summary of the article's content and significance",
        },
        "key_findings": {
            "type": "string",
            "description": "Bullet-point list of the most important findings or arguments",
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
                        "enum": ["topic", "stance", "methodology", "policy_area"],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
        "relevance_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "How relevant is this to AI policy in higher education? 0=not relevant, 1=highly relevant",
        },
        "content_type": {
            "type": "string",
            "enum": ["article", "paper", "report", "blog_post", "policy_document", "news", "other"],
        },
        "word_count": {
            "type": "integer",
            "description": "Estimated word count of the full article",
        },
    },
}

SYSTEM_PROMPT = """You are an AI research librarian specializing in AI policy for higher education institutions.

Analyze the article information provided and produce a structured enrichment with:
1. A clear 2-3 paragraph summary capturing the main arguments and significance
2. Key findings as a bullet-point list
3. Relevant tags across these categories:
   - topic: subject matter (e.g., "academic integrity", "generative ai", "assessment")
   - stance: perspective (e.g., "pro-regulation", "cautious optimism", "critical")
   - methodology: research approach (e.g., "qualitative study", "policy analysis", "opinion")
   - policy_area: institutional domain (e.g., "teaching", "research", "administration")
4. A relevance score (0-1) for how useful this is to a college AI policy working group
5. Content type classification
6. Estimated word count"""


def enrich_article(db: Session, article: Article) -> bool:
    """Enrich a single article with AI-generated metadata. Returns True on success."""
    user_prompt = f"""Article to analyze:
Title: {article.title}
URL: {article.url}
Source: {article.source}
Content Type: {article.content_type}
Published: {article.published_date or 'Unknown'}

Please analyze this article and provide the structured enrichment."""

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
    article.word_count = result["word_count"]
    article.reading_time_minutes = estimate_reading_time(result["word_count"])
    article.status = "enriched"

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
    """Enrich up to batch_size pending articles. Returns summary stats."""
    articles = (
        db.query(Article)
        .filter(Article.status == "pending")
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
