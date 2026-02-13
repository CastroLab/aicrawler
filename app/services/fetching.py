import hashlib
import logging
import datetime as dt

import httpx
import trafilatura

from sqlalchemy.orm import Session

from app.models.article import Article, ArticleAuthor
from app.models.content import ArticleContent

logger = logging.getLogger(__name__)

PAYWALL_INDICATORS = [
    "subscribe to continue",
    "subscribe to read",
    "this content is for subscribers",
    "paywall",
    "sign in to read",
    "create a free account",
    "premium content",
    "members only",
]

FETCH_TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (compatible; AICrawler/1.0; +https://github.com/aicrawler)"
)


def fetch_article_content(db: Session, article: Article) -> bool:
    """Fetch and extract content for a single article. Returns True on success."""
    # Get or create ArticleContent record
    content = (
        db.query(ArticleContent)
        .filter(ArticleContent.article_id == article.id)
        .first()
    )
    if not content:
        content = ArticleContent(article_id=article.id, fetch_status="pending")
        db.add(content)
        db.flush()

    try:
        response = httpx.get(
            article.url,
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        content.http_status = response.status_code

        if response.status_code != 200:
            content.fetch_status = "failed"
            content.fetch_error = f"HTTP {response.status_code}"
            content.fetched_at = dt.datetime.now(dt.timezone.utc)
            article.status = "fetch_failed"
            db.commit()
            return False

        html = response.text

        # Check for paywall indicators in raw HTML
        html_lower = html.lower()
        is_paywall = any(indicator in html_lower for indicator in PAYWALL_INDICATORS)

        # Extract content with trafilatura
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            output_format="txt",
        )

        # Extract metadata
        metadata = trafilatura.extract_metadata(html)

        if not extracted or len(extracted.strip()) < 100:
            if is_paywall:
                content.fetch_status = "paywall"
                content.fetch_error = "Content appears to be behind a paywall"
            else:
                content.fetch_status = "failed"
                content.fetch_error = "Could not extract meaningful content"
            content.fetched_at = dt.datetime.now(dt.timezone.utc)
            article.status = "fetch_failed"
            db.commit()
            return False

        # Store extracted content
        content.full_text = extracted
        content.content_hash = hashlib.sha256(extracted.encode()).hexdigest()
        content.word_count = len(extracted.split())
        content.fetched_at = dt.datetime.now(dt.timezone.utc)

        if is_paywall and len(extracted.split()) < 200:
            content.fetch_status = "partial"
            content.fetch_error = "Partial content - possible paywall"
        else:
            content.fetch_status = "success"

        # Backfill metadata from extraction
        if metadata:
            if metadata.title:
                content.extracted_title = metadata.title
            if metadata.author:
                content.extracted_author = metadata.author
                # Backfill author to article if none exists
                if not article.authors:
                    db.add(ArticleAuthor(article_id=article.id, name=metadata.author))
            if metadata.date:
                content.extracted_date = str(metadata.date)

        # Update article
        article.has_content = True
        article.status = "fetched"
        if content.word_count:
            article.word_count = content.word_count
            article.reading_time_minutes = max(1, round(content.word_count / 238))

        db.commit()
        logger.info(
            "Fetched article %d: %s (%d words)",
            article.id,
            article.title[:60],
            content.word_count or 0,
        )
        return True

    except httpx.TimeoutException:
        content.fetch_status = "failed"
        content.fetch_error = "Request timed out"
        content.fetched_at = dt.datetime.now(dt.timezone.utc)
        article.status = "fetch_failed"
        db.commit()
        logger.warning("Timeout fetching article %d: %s", article.id, article.url)
        return False

    except Exception as e:
        content.fetch_status = "failed"
        content.fetch_error = str(e)[:500]
        content.fetched_at = dt.datetime.now(dt.timezone.utc)
        article.status = "fetch_failed"
        db.commit()
        logger.exception("Failed to fetch article %d", article.id)
        return False


def fetch_pending_articles(db: Session, batch_size: int = 20) -> dict:
    """Fetch content for pending articles. Returns summary stats."""
    articles = (
        db.query(Article)
        .filter(Article.status == "pending")
        .order_by(Article.created_at)
        .limit(batch_size)
        .all()
    )

    stats = {"total": len(articles), "success": 0, "failed": 0}
    for article in articles:
        if fetch_article_content(db, article):
            stats["success"] += 1
        else:
            stats["failed"] += 1

    logger.info("Fetch batch: %s", stats)
    return stats
