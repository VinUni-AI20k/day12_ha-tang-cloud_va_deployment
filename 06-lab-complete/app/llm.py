import json
import logging
from typing import Any, Optional

import httpx

from app.config import settings
from utils.mock_llm import ask as mock_ask

logger = logging.getLogger(__name__)


def get_llm_provider() -> str:
    if settings.dashscope_api_key and settings.dashscope_endpoint:
        return "dashscope"
    return "mock"


def _dashscope_url(endpoint: str) -> str:
    """Return a request URL for DashScope.

    For OpenAI-compatible mode, users typically set endpoint to:
    `https://.../compatible-mode/v1` and the actual route is `/chat/completions`.
    """
    ep = (endpoint or "").strip().rstrip("/")
    if not ep:
        return ep

    if ep.endswith("/chat/completions"):
        return ep

    # DashScope OpenAI-compatible route
    if "/compatible-mode/" in ep or ep.endswith("/v1"):
        return f"{ep}/chat/completions"

    # Fallback: keep as-is (caller may pass full path)
    return ep


def _extract_text(response_json: dict[str, Any]) -> Optional[str]:
    # Common DashScope shapes (try a few)
    output = response_json.get("output")
    if isinstance(output, dict):
        text = output.get("text")
        if isinstance(text, str) and text.strip():
            return text

        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            choice0 = choices[0] if isinstance(choices[0], dict) else None
            if choice0:
                message = choice0.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content
                text2 = choice0.get("text")
                if isinstance(text2, str) and text2.strip():
                    return text2

    # Some APIs return `choices` at top-level
    choices_top = response_json.get("choices")
    if isinstance(choices_top, list) and choices_top:
        choice0 = choices_top[0] if isinstance(choices_top[0], dict) else None
        if choice0:
            message = choice0.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
            text3 = choice0.get("text")
            if isinstance(text3, str) and text3.strip():
                return text3

    return None


async def ask_llm(question: str) -> str:
    """Ask Qwen via DashScope (if configured), otherwise fall back to mock."""
    if get_llm_provider() == "mock":
        return mock_ask(question)

    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }

    url = _dashscope_url(settings.dashscope_endpoint)

    # OpenAI-compatible payload for `.../compatible-mode/v1/chat/completions`
    payload: dict[str, Any] = {
        "model": settings.qwen_model,
        "messages": [
            {"role": "user", "content": question},
        ],
        "stream": False,
    }

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code >= 400:
        # Avoid logging secrets; only log status + short body
        body_preview = resp.text[:500]
        logger.error(json.dumps({
            "event": "llm_error",
            "provider": "dashscope",
            "status": resp.status_code,
            "body_preview": body_preview,
        }))
        raise RuntimeError(f"DashScope LLM error: HTTP {resp.status_code}")

    data = resp.json()
    text = _extract_text(data)
    if not text:
        logger.error(json.dumps({
            "event": "llm_bad_response",
            "provider": "dashscope",
            "keys": list(data.keys()),
        }))
        raise RuntimeError("DashScope response missing text")

    return text
