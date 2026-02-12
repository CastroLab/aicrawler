from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def current_user(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return {
        "id": user_id,
        "username": request.session.get("username", ""),
        "role": request.session.get("role", "member"),
    }


def require_login(request: Request):
    user = current_user(request)
    if not user:
        raise _LoginRequired()
    return user


def require_admin(request: Request):
    user = require_login(request)
    if user["role"] != "admin":
        raise _LoginRequired()
    return user


class _LoginRequired(Exception):
    pass
