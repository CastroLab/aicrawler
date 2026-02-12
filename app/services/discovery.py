import datetime as dt
import logging
import re

from sqlalchemy.orm import Session

from app.clients.perplexity import search_perplexity
from app.models.article import Article
from app.models.search_job import SearchExecution, SearchJob
from app.services.dedup import url_hash

logger = logging.getLogger(__name__)


def _extract_title_from_url(url: str) -> str:
    """Best-effort title extraction from URL path."""
    from urllib.parse import urlparse

    path = urlparse(url).path.strip("/")
    if not path:
        return url
    last_segment = path.split("/")[-1]
    # Remove file extensions
    last_segment = re.sub(r"\.\w+$", "", last_segment)
    # Replace hyphens/underscores with spaces
    title = re.sub(r"[-_]", " ", last_segment)
    return title.title()[:200] or url


def _parse_citations(content: str, citations: list[str]) -> list[dict]:
    """Parse Perplexity response into article candidates.

    Returns list of {url, title, source} dicts.
    """
    articles = []
    seen_urls = set()

    for url in citations:
        url = url.strip().rstrip(".")
        if not url.startswith("http"):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        from urllib.parse import urlparse

        parsed = urlparse(url)
        source = parsed.hostname or ""
        if source.startswith("www."):
            source = source[4:]

        title = _extract_title_from_url(url)
        articles.append({"url": url, "title": title, "source": source})

    return articles


def run_search_job(db: Session, job: SearchJob) -> SearchExecution:
    """Run a single search job and create articles from results."""
    execution = SearchExecution(
        search_job_id=job.id,
        status="running",
    )
    db.add(execution)
    db.commit()

    try:
        result = search_perplexity(job.query)
        if not result:
            execution.status = "error"
            execution.error_message = "Perplexity API returned no result"
            execution.finished_at = dt.datetime.utcnow()
            db.commit()
            return execution

        candidates = _parse_citations(result["content"], result["citations"])
        execution.articles_found = len(candidates)
        new_count = 0

        for candidate in candidates:
            hash_ = url_hash(candidate["url"])
            existing = db.query(Article).filter(Article.url_hash == hash_).first()
            if existing:
                continue

            article = Article(
                url=candidate["url"],
                url_hash=hash_,
                title=candidate["title"],
                source=candidate["source"],
                status="pending",
            )
            db.add(article)
            new_count += 1

        execution.articles_new = new_count
        execution.status = "completed"
        execution.finished_at = dt.datetime.utcnow()
        db.commit()

        logger.info(
            "Search job '%s': found %d, new %d",
            job.name,
            execution.articles_found,
            new_count,
        )
        return execution

    except Exception as e:
        execution.status = "error"
        execution.error_message = str(e)[:500]
        execution.finished_at = dt.datetime.utcnow()
        db.commit()
        logger.exception("Search job '%s' failed", job.name)
        return execution


def run_all_search_jobs(db: Session) -> dict:
    """Run all enabled search jobs. Returns summary stats."""
    jobs = db.query(SearchJob).filter(SearchJob.enabled == True).all()
    stats = {"jobs_run": 0, "total_found": 0, "total_new": 0}

    for job in jobs:
        execution = run_search_job(db, job)
        stats["jobs_run"] += 1
        stats["total_found"] += execution.articles_found
        stats["total_new"] += execution.articles_new

    logger.info("Discovery complete: %s", stats)
    return stats
