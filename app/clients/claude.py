import json
import logging

import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_claude_client() -> anthropic.Anthropic | None:
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — Claude features disabled")
        return None
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def call_claude_structured(
    system_prompt: str,
    user_prompt: str,
    response_schema: dict,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 4096,
) -> dict | None:
    """Call Claude with structured JSON output.

    Uses tool_use to enforce a JSON schema on the response.
    Returns the parsed dict or None on failure.
    """
    client = get_claude_client()
    if not client:
        return None

    tool = {
        "name": "structured_response",
        "description": "Provide the structured response",
        "input_schema": response_schema,
    }

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[tool],
            tool_choice={"type": "tool", "name": "structured_response"},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "structured_response":
                return block.input

        logger.error("No structured response found in Claude output")
        return None

    except Exception:
        logger.exception("Claude API call failed")
        return None
