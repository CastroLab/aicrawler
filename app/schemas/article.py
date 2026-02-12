import datetime as dt

from pydantic import BaseModel, HttpUrl


class ArticleCreate(BaseModel):
    url: str
    title: str
    source: str = ""
    published_date: dt.date | None = None
    content_type: str = "article"
    authors: list[str] = []


class ArticleUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    published_date: dt.date | None = None
    content_type: str | None = None
    summary: str | None = None
    key_findings: str | None = None
    relevance_score: float | None = None
    status: str | None = None


class TagOut(BaseModel):
    name: str
    category: str
    confidence: float = 1.0


class ArticleOut(BaseModel):
    id: int
    url: str
    title: str
    source: str
    published_date: dt.date | None
    content_type: str
    summary: str | None
    key_findings: str | None
    relevance_score: float | None
    word_count: int | None
    reading_time_minutes: int | None
    status: str
    created_at: dt.datetime
    authors: list[str] = []
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}


class EnrichmentResult(BaseModel):
    summary: str
    key_findings: str
    tags: list[dict]  # [{name, category, confidence}]
    relevance_score: float
    content_type: str
    word_count: int
