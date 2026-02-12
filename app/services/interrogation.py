import json
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.clients.claude import call_claude_structured
from app.models.article import Article
from app.models.query_log import InterrogationLog
from app.models.reading_list import ReadingList, ReadingListItem
from app.models.tag import ArticleTag, Tag

logger = logging.getLogger(__name__)

QUERY_PLAN_SCHEMA = {
    "type": "object",
    "required": ["search_terms", "max_articles", "sort_by"],
    "properties": {
        "search_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Keywords and phrases for full-text search",
        },
        "tag_filters": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tag names to filter by",
        },
        "time_budget_minutes": {
            "type": "integer",
            "description": "Maximum total reading time in minutes, or null for no limit",
        },
        "require_contrasting": {
            "type": "boolean",
            "description": "Whether to include contrasting viewpoints",
        },
        "content_types": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Preferred content types",
        },
        "max_articles": {
            "type": "integer",
            "description": "Maximum number of articles to include",
        },
        "sort_by": {
            "type": "string",
            "enum": ["relevance", "date", "reading_time"],
        },
    },
}

SYNTHESIS_SCHEMA = {
    "type": "object",
    "required": ["title", "description", "sections", "discussion_prompts", "total_reading_time"],
    "properties": {
        "title": {"type": "string", "description": "Reading list title"},
        "description": {
            "type": "string",
            "description": "Brief description of the reading list and what it covers",
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "article_ids", "notes"],
                "properties": {
                    "title": {"type": "string"},
                    "article_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "IDs of articles in this section",
                    },
                    "notes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Reading notes or context for this section",
                    },
                },
            },
        },
        "discussion_prompts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Discussion questions for a working group meeting",
        },
        "total_reading_time": {
            "type": "integer",
            "description": "Total estimated reading time in minutes",
        },
    },
}


def _phase1_plan(query: str) -> dict | None:
    """Phase 1: Parse natural language query into structured query plan."""
    return call_claude_structured(
        system_prompt=(
            "You are a research librarian. Parse the user's natural language query into "
            "a structured search plan. Extract search terms, tag preferences, time budget, "
            "and whether contrasting views are needed."
        ),
        user_prompt=query,
        response_schema=QUERY_PLAN_SCHEMA,
    )


def _execute_search(db: Session, plan: dict) -> list[Article]:
    """Execute the query plan against the database."""
    candidate_ids = set()

    # FTS5 search for each search term
    for term in plan.get("search_terms", []):
        try:
            result = db.execute(
                text("SELECT rowid FROM articles_fts WHERE articles_fts MATCH :q ORDER BY rank LIMIT 50"),
                {"q": term},
            )
            for row in result:
                candidate_ids.add(row[0])
        except Exception:
            logger.debug("FTS search failed for term: %s", term)

    # If no FTS results, fall back to all enriched articles
    if not candidate_ids:
        fallback = (
            db.query(Article.id)
            .filter(Article.status == "enriched")
            .order_by(Article.relevance_score.desc().nullslast())
            .limit(50)
            .all()
        )
        candidate_ids = {row[0] for row in fallback}

    if not candidate_ids:
        return []

    query = (
        db.query(Article)
        .options(
            joinedload(Article.article_tags).joinedload(ArticleTag.tag),
            joinedload(Article.authors),
        )
        .filter(Article.id.in_(candidate_ids))
    )

    # Tag filters
    tag_filters = plan.get("tag_filters", [])
    if tag_filters:
        query = query.join(ArticleTag).join(Tag).filter(Tag.name.in_(tag_filters))

    # Content type filter
    content_types = plan.get("content_types", [])
    if content_types:
        query = query.filter(Article.content_type.in_(content_types))

    articles = query.all()

    # Deduplicate (joinedload may create duplicates)
    seen = set()
    unique = []
    for a in articles:
        if a.id not in seen:
            seen.add(a.id)
            unique.append(a)

    # Sort
    sort_by = plan.get("sort_by", "relevance")
    if sort_by == "relevance":
        unique.sort(key=lambda a: a.relevance_score or 0, reverse=True)
    elif sort_by == "date":
        unique.sort(key=lambda a: a.published_date or "", reverse=True)
    elif sort_by == "reading_time":
        unique.sort(key=lambda a: a.reading_time_minutes or 0)

    # Apply time budget
    time_budget = plan.get("time_budget_minutes")
    if time_budget:
        selected = []
        total_time = 0
        for a in unique:
            rt = a.reading_time_minutes or 5
            if total_time + rt <= time_budget:
                selected.append(a)
                total_time += rt
        unique = selected

    # Limit
    max_articles = plan.get("max_articles", 10)
    return unique[:max_articles]


def _phase2_synthesize(query: str, articles: list[Article]) -> dict | None:
    """Phase 2: Claude synthesizes a reading list from candidate articles."""
    articles_info = []
    for a in articles:
        tags = [at.tag.name for at in a.article_tags] if a.article_tags else []
        articles_info.append({
            "id": a.id,
            "title": a.title,
            "source": a.source,
            "summary": (a.summary or "")[:500],
            "tags": tags,
            "relevance_score": a.relevance_score,
            "reading_time_minutes": a.reading_time_minutes,
            "content_type": a.content_type,
        })

    return call_claude_structured(
        system_prompt=(
            "You are a research librarian creating a curated reading list for a college "
            "AI policy working group. Organize the provided articles into thematic sections, "
            "add reading notes, and create discussion prompts for a committee meeting. "
            "Only use article IDs from the provided list."
        ),
        user_prompt=f"""Original query: {query}

Available articles:
{json.dumps(articles_info, indent=2)}

Create a structured reading list with sections, notes, and discussion prompts.""",
        response_schema=SYNTHESIS_SCHEMA,
    )


def process_query(db: Session, query: str, user_id: int | None = None) -> dict:
    """Full two-phase interrogation pipeline.

    Returns a result dict suitable for template rendering.
    """
    # Phase 1: Parse query
    plan = _phase1_plan(query)
    if not plan:
        return _fallback_result(db, query, user_id, "Could not parse query")

    # Execute search
    articles = _execute_search(db, plan)
    if not articles:
        return _fallback_result(db, query, user_id, "No matching articles found")

    # Phase 2: Synthesize
    synthesis = _phase2_synthesize(query, articles)
    if not synthesis:
        return _fallback_result(db, query, user_id, "Could not generate reading list")

    # Save reading list to DB
    reading_list = ReadingList(
        title=synthesis["title"],
        description=synthesis["description"],
        query=query,
        discussion_prompts="\n".join(synthesis.get("discussion_prompts", [])),
        total_reading_time=synthesis.get("total_reading_time"),
        created_by=user_id,
    )
    db.add(reading_list)
    db.flush()

    # Map articles by ID for quick lookup
    article_map = {a.id: a for a in articles}

    for section in synthesis.get("sections", []):
        for i, article_id in enumerate(section.get("article_ids", [])):
            if article_id in article_map:
                db.add(
                    ReadingListItem(
                        reading_list_id=reading_list.id,
                        article_id=article_id,
                        section=section["title"],
                        position=i,
                        notes=section["notes"][i] if i < len(section.get("notes", [])) else None,
                    )
                )

    # Log the query
    log_entry = InterrogationLog(
        user_id=user_id,
        query=query,
        query_plan=json.dumps(plan),
        result=json.dumps(synthesis),
        reading_list_id=reading_list.id,
    )
    db.add(log_entry)
    db.commit()

    # Build template-friendly result
    sections_data = []
    for section in synthesis.get("sections", []):
        articles_data = []
        for aid in section.get("article_ids", []):
            if aid in article_map:
                a = article_map[aid]
                articles_data.append({
                    "id": a.id,
                    "title": a.title,
                    "source": a.source,
                    "reading_time_minutes": a.reading_time_minutes,
                })
        sections_data.append({
            "title": section["title"],
            "articles_data": articles_data,
            "notes": section.get("notes", []),
        })

    return {
        "title": synthesis["title"],
        "description": synthesis["description"],
        "sections": sections_data,
        "discussion_prompts": synthesis.get("discussion_prompts", []),
        "total_reading_time": synthesis.get("total_reading_time", 0),
        "reading_list_id": reading_list.id,
    }


def _fallback_result(db: Session, query: str, user_id: int | None, error: str) -> dict:
    """Return a minimal result when the pipeline fails."""
    log_entry = InterrogationLog(
        user_id=user_id,
        query=query,
        result=json.dumps({"error": error}),
    )
    db.add(log_entry)
    db.commit()

    return {
        "title": "Query could not be processed",
        "description": error,
        "sections": [],
        "discussion_prompts": [],
        "total_reading_time": 0,
        "reading_list_id": None,
    }
