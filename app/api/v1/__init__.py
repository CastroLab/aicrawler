from fastapi import APIRouter

from app.api.v1.articles import router as articles_router
from app.api.v1.pipeline import router as pipeline_router
from app.api.v1.digests import router as digests_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(articles_router, prefix="/articles", tags=["articles"])
api_router.include_router(pipeline_router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(digests_router, prefix="/digests", tags=["digests"])
