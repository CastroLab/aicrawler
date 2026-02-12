from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_login, templates
from app.models.article import Article, ArticleAuthor
from app.models.tag import ArticleTag, Tag
from app.services.dedup import url_hash

router = APIRouter(tags=["articles"])

PER_PAGE = 20


@router.get("/", response_class=HTMLResponse)
async def list_articles(
    request: Request,
    q: str = "",
    tag: str = "",
    status: str = "",
    page: int = 1,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    query = db.query(Article).options(
        joinedload(Article.article_tags).joinedload(ArticleTag.tag),
        joinedload(Article.authors),
    )

    if q:
        # FTS5 search
        fts_sql = text(
            "SELECT rowid FROM articles_fts WHERE articles_fts MATCH :q ORDER BY rank"
        )
        result = db.execute(fts_sql, {"q": q})
        ids = [row[0] for row in result]
        if ids:
            query = query.filter(Article.id.in_(ids))
        else:
            query = query.filter(False)

    if tag:
        query = query.join(ArticleTag).join(Tag).filter(Tag.name == tag)

    if status:
        query = query.filter(Article.status == status)

    total = query.count()
    articles = (
        query.order_by(Article.created_at.desc())
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )
    # Make articles unique (joinedload can duplicate)
    seen = set()
    unique_articles = []
    for a in articles:
        if a.id not in seen:
            seen.add(a.id)
            unique_articles.append(a)

    all_tags = db.query(Tag).order_by(Tag.name).all()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    return templates.TemplateResponse(
        "articles/list.html",
        {
            "request": request,
            "user": user,
            "articles": unique_articles,
            "q": q,
            "tag": tag,
            "status": status,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "all_tags": all_tags,
        },
    )


@router.get("/add", response_class=HTMLResponse)
async def add_article_form(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse(
        "articles/add.html", {"request": request, "user": user}
    )


@router.post("/add")
async def add_article(
    request: Request,
    url: str = Form(...),
    title: str = Form(...),
    source: str = Form(""),
    published_date: str = Form(""),
    content_type: str = Form("article"),
    authors: str = Form(""),
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    hash_ = url_hash(url)
    existing = db.query(Article).filter(Article.url_hash == hash_).first()
    if existing:
        return templates.TemplateResponse(
            "articles/add.html",
            {
                "request": request,
                "user": user,
                "error": f"Article already exists: {existing.title}",
                "url": url,
                "title": title,
            },
            status_code=409,
        )

    import datetime as dt

    pub_date = None
    if published_date:
        try:
            pub_date = dt.date.fromisoformat(published_date)
        except ValueError:
            pass

    article = Article(
        url=url,
        url_hash=hash_,
        title=title,
        source=source,
        published_date=pub_date,
        content_type=content_type,
        status="pending",
    )
    db.add(article)
    db.flush()

    if authors.strip():
        for name in authors.split(","):
            name = name.strip()
            if name:
                db.add(ArticleAuthor(article_id=article.id, name=name))

    db.commit()
    return RedirectResponse(f"/articles/{article.id}", status_code=303)


@router.get("/{article_id}", response_class=HTMLResponse)
async def article_detail(
    request: Request,
    article_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    article = (
        db.query(Article)
        .options(
            joinedload(Article.article_tags).joinedload(ArticleTag.tag),
            joinedload(Article.authors),
        )
        .filter(Article.id == article_id)
        .first()
    )
    if not article:
        return templates.TemplateResponse(
            "404.html", {"request": request, "user": user}, status_code=404
        )
    return templates.TemplateResponse(
        "articles/detail.html",
        {"request": request, "user": user, "article": article},
    )


@router.post("/{article_id}/delete")
async def delete_article(
    article_id: int,
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if article:
        db.delete(article)
        db.commit()
    return RedirectResponse("/articles", status_code=303)
