import logging
import re

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_perplexity_client() -> OpenAI | None:
    settings = get_settings()
    if not settings.PERPLEXITY_API_KEY:
        logger.warning("PERPLEXITY_API_KEY not set — discovery disabled")
        return None
    return OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )


def search_perplexity(query: str, model: str = "sonar") -> dict | None:
    """Run a search query against Perplexity Sonar API.

    Returns {"content": str, "citations": list[str]} or None on failure.
    """
    client = get_perplexity_client()
    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant finding recent articles, papers, and reports "
                        "about AI policy in higher education. For each source you find, provide the "
                        "full URL and a brief description. Focus on reputable sources."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        message = response.choices[0].message
        content = message.content or ""

        # Extract citations from response
        citations = []
        if hasattr(response, "citations") and response.citations:
            citations = list(response.citations)
        else:
            # Fall back to extracting URLs from content
            citations = re.findall(r'https?://[^\s\)\]>"]+', content)

        return {"content": content, "citations": citations}

    except Exception:
        logger.exception("Perplexity API call failed")
        return None
