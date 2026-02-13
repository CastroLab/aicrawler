import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.v1.auth import require_api_token
from app.database import get_db
from app.models.article import Article, ArticleAuthor
from app.models.content import ArticleContent
from app.models.tag import ArticleTag
from app.schemas.article import ArticleCreate, ArticleOut, ArticleUpdate, TagOut
from app.schemas.content import ArticleContentOut
from app.services.dedup import normalize_url, url_hash

router = APIRouter(dependencies=[Depends(require_api_token)])


def _article_to_out(article: Article) -> dict:
    """Convert Article ORM object to API-friendly dict."""
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "source": article.source,
        "published_date": article.published_date,
        "content_type": article.content_type,
        "summary": article.summary,
        "key_findings": article.key_findings,
        "relevance_score": article.relevance_score,
        "word_count": article.word_count,
        "reading_time_minutes": article.reading_time_minutes,
        "status": article.status,
        "has_content": article.has_content,
        "created_at": article.created_at,
        "authors": [a.name for a in article.authors],
        "tags": [
            {"name": at.tag.name, "category": at.tag.category, "confidence": at.confidence}
            for at in article.article_tags
            if at.tag
        ],
    }


@router.get("")
async def list_articles(
    db: Session = Depends(get_db),
    status: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List articles with optional filtering."""
    query = db.query(Article).options(
        joinedload(Article.authors),
        joinedload(Article.article_tags).joinedload(ArticleTag.tag),
    )

    if status:
        query = query.filter(Article.status == status)
    if tag:
        query = query.join(Article.article_tags).join(ArticleTag.tag).filter(
            ArticleTag.tag.has(name=tag)
        )
    if q:
        query = query.filter(
            Article.title.ilike(f"%{q}%") | Article.summary.ilike(f"%{q}%")
        )

    total = query.count()
    articles = (
        query.order_by(Article.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    # Deduplicate from joinedload
    seen = set()
    unique = []
    for a in articles:
        if a.id not in seen:
            seen.add(a.id)
            unique.append(a)

    return {
        "items": [_article_to_out(a) for a in unique],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", status_code=201)
async def create_article(
    data: ArticleCreate,
    db: Session = Depends(get_db),
):
    """Create a new article."""
    normalized = normalize_url(data.url)
    hash_val = url_hash(data.url)

    existing = db.query(Article).filter(Article.url_hash == hash_val).first()
    if existing:
        raise HTTPException(status_code=409, detail="Article with this URL already exists")

    article = Article(
        url=normalized,
        url_hash=hash_val,
        title=data.title,
        source=data.source,
        published_date=data.published_date,
        content_type=data.content_type,
        status="pending",
    )
    db.add(article)
    db.flush()

    for author_name in data.authors:
        db.add(ArticleAuthor(article_id=article.id, name=author_name))

    db.commit()
    db.refresh(article)
    return _article_to_out(article)


@router.get("/{article_id}")
async def get_article(
    article_id: int,
    db: Session = Depends(get_db),
):
    """Get a single article by ID."""
    article = (
        db.query(Article)
        .options(
            joinedload(Article.authors),
            joinedload(Article.article_tags).joinedload(ArticleTag.tag),
        )
        .filter(Article.id == article_id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_to_out(article)


@router.patch("/{article_id}")
async def update_article(
    article_id: int,
    data: ArticleUpdate,
    db: Session = Depends(get_db),
):
    """Update article fields."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(article, field, value)

    db.commit()
    db.refresh(article)
    return _article_to_out(article)


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
):
    """Delete an article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()


@router.get("/{article_id}/content")
async def get_article_content(
    article_id: int,
    db: Session = Depends(get_db),
):
    """Get fetched content for an article."""
    content = (
        db.query(ArticleContent)
        .filter(ArticleContent.article_id == article_id)
        .first()
    )
    if not content:
        raise HTTPException(status_code=404, detail="No content fetched for this article")
    return ArticleContentOut.model_validate(content)


@router.post("/{article_id}/fetch")
async def fetch_article(
    article_id: int,
    db: Session = Depends(get_db),
):
    """Trigger content fetching for a specific article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    from app.services.fetching import fetch_article_content

    success = fetch_article_content(db, article)
    return {"success": success, "status": article.status}


@router.post("/{article_id}/enrich")
async def enrich_article_endpoint(
    article_id: int,
    db: Session = Depends(get_db),
):
    """Trigger enrichment for a specific article."""
    article = (
        db.query(Article)
        .options(joinedload(Article.authors))
        .filter(Article.id == article_id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    from app.services.enrichment import enrich_article

    success = enrich_article(db, article)
    return {"success": success, "status": article.status}
