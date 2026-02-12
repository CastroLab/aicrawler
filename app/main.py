from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.deps import _LoginRequired, current_user, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize scheduler (Phase 5)
    from app.scheduler.setup import start_scheduler

    scheduler = start_scheduler()
    yield
    # Shutdown
    if scheduler:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_TITLE, lifespan=lifespan)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register routes
    from app.routes.auth import router as auth_router
    from app.routes.articles import router as articles_router
    from app.routes.dashboard import router as dashboard_router
    from app.routes.search_jobs import router as search_jobs_router
    from app.routes.interrogation import router as interrogation_router
    from app.routes.reading_lists import router as reading_lists_router
    from app.routes.admin import router as admin_router

    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(articles_router, prefix="/articles")
    app.include_router(search_jobs_router, prefix="/search-jobs")
    app.include_router(interrogation_router, prefix="/interrogation")
    app.include_router(reading_lists_router, prefix="/reading-lists")
    app.include_router(admin_router, prefix="/admin")

    @app.exception_handler(_LoginRequired)
    async def login_required_handler(request: Request, exc: _LoginRequired):
        return RedirectResponse("/login", status_code=303)

    # Inject current_user into template globals via Jinja2 context
    def _template_globals(request: Request) -> dict:
        try:
            user = current_user(request)
        except Exception:
            user = None
        return user

    # Use Jinja2 globals to access request.state.user in templates
    templates.env.globals["app_title"] = settings.APP_TITLE

    # Add SessionMiddleware last so it wraps everything
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="aicrawler_session",
        max_age=86400 * 7,
    )

    return app


app = create_app()
