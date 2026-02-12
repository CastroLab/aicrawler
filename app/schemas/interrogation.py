from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class QueryPlan(BaseModel):
    search_terms: list[str]
    tag_filters: list[str] = []
    time_budget_minutes: int | None = None
    require_contrasting: bool = False
    content_types: list[str] = []
    max_articles: int = 10
    sort_by: str = "relevance"


class ReadingListSection(BaseModel):
    title: str
    articles: list[int]  # article IDs
    notes: list[str] = []


class QueryResult(BaseModel):
    title: str
    description: str
    sections: list[ReadingListSection]
    discussion_prompts: list[str]
    total_reading_time: int
