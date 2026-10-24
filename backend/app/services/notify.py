"""Optional Slack notifications through an incoming webhook (SLACK_WEBHOOK_URL). Titles and statuses only, never draft text."""
import logging

from app.core.config import get_settings

log = logging.getLogger("brandsure")


def enabled() -> bool:
    return bool(get_settings().slack_webhook_url)


def notify(text: str) -> None:
    url = get_settings().slack_webhook_url
    if not url:
        return
    try:
        import httpx
        httpx.post(url, json={"text": text}, timeout=5)
    except Exception:  # a failed notification must never break the workflow
        log.warning("Slack notification failed")
