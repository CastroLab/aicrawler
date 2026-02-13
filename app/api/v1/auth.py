from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer_scheme = HTTPBearer()


def require_api_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """Validate Bearer token against configured API_TOKEN."""
    settings = get_settings()
    if not settings.API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="API_TOKEN not configured. Set API_TOKEN in .env to enable API access.",
        )
    if credentials.credentials != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return credentials.credentials
