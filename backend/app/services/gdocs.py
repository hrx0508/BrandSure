"""Import text from a Google Doc that is shared as 'Anyone with the link can view' (no Google credentials needed)."""
import re

from app.core.errors import AppError

GDOC_RE = re.compile(r"^https://docs\.google\.com/document/d/([A-Za-z0-9_-]{10,})")
MAX_BYTES = 1_000_000


def doc_id(url: str) -> str:
    m = GDOC_RE.match((url or "").strip())
    if not m:
        raise AppError(400, "INVALID_URL", "Paste a Google Docs link that starts with https://docs.google.com/document/d/")
    return m.group(1)


def fetch_text(url: str) -> str:
    did = doc_id(url)
    import httpx
    export = f"https://docs.google.com/document/d/{did}/export?format=txt"  # host is fixed: no user-controlled requests
    try:
        r = httpx.get(export, follow_redirects=True, timeout=15)
    except httpx.HTTPError as e:
        raise AppError(502, "GDOC_UNREACHABLE", "Google Docs could not be reached. Try again, or upload the file instead.") from e
    ctype = r.headers.get("content-type", "")
    if r.status_code != 200 or "text/plain" not in ctype:
        raise AppError(400, "GDOC_NOT_SHARED", "Set the document's sharing to \u201cAnyone with the link can view\u201d, or download it as DOCX and upload that.")
    if len(r.content) > MAX_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "This document is too large to import.")
    return r.text.lstrip("\ufeff")
