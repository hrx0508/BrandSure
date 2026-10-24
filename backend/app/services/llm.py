"""LLM provider hidden behind a few functions. They return None / raise LLMError when no API key is configured."""
import json
import re

from app.core.config import get_settings


class LLMError(Exception):
    pass


def configured() -> bool:
    return bool(get_settings().llm_api_key)


def _post(system: str, content, max_tokens: int) -> str:
    s = get_settings()
    import httpx  # imported lazily: only needed when an API key is configured
    try:
        r = httpx.post(
            s.llm_url,
            headers={"x-api-key": s.llm_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": s.llm_model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": content}]},
            timeout=60,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    except httpx.HTTPError as e:
        raise LLMError("The AI service is unavailable or rate-limited.") from e


def complete_json(system: str, user: str, max_tokens: int = 2000):
    if not configured():
        return None
    text = re.sub(r"^```(?:json)?|```$", "", _post(system, user, max_tokens).strip(), flags=re.M).strip()
    try:
        return json.loads(text[text.index("{"): text.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError) as e:
        raise LLMError("The AI returned malformed output.") from e


def complete_text(system: str, user: str, image_data_uri: str | None = None, max_tokens: int = 200) -> str:
    """Plain-text answer, optionally about one image (a base64 data URI)."""
    if not configured():
        raise LLMError("AI is not configured.")
    content = user
    if image_data_uri:
        head, _, b64 = image_data_uri.partition(",")
        media = head.split(";")[0].replace("data:", "") or "image/jpeg"
        content = [{"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}}, {"type": "text", "text": user}]
    return _post(system, content, max_tokens).strip()
