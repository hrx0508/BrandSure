from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.security import User, require_role
from app.services import document_extractor, llm, notify

router = APIRouter(tags=["integrations"])


@router.get("/integrations")
def integrations(user: User = Depends(require_role("admin"))):
    """Which optional services are switched on. Values are never shown; names tell the admin what to fill in."""
    s = get_settings()
    return {"integrations": [
        {"id": "ai", "name": "AI analysis and alt-text help", "configured": llm.configured(), "env": ["LLM_API_KEY", "LLM_MODEL"],
         "note": "Used for tone and claim judgement, guideline rule extraction and alt-text suggestions. Every AI answer is validated first."},
        {"id": "slack", "name": "Slack notifications", "configured": notify.enabled(), "env": ["SLACK_WEBHOOK_URL"],
         "note": "Posts titles and statuses (never draft text) when a kit is sent, a post is sent for review or a decision is made."},
        {"id": "google_docs", "name": "Google Docs import", "configured": True, "env": [],
         "note": "Works for documents shared as \u201cAnyone with the link can view\u201d. No Google credentials needed."},
        {"id": "ocr", "name": "OCR for scanned PDFs", "configured": document_extractor.ocr_available(), "env": ["OCR_ENABLED", "OCR_LANG"],
         "note": "Needs the Tesseract program and the pytesseract package on the server (see docs/INTEGRATIONS.md)."},
        {"id": "supabase", "name": "Supabase Auth", "configured": s.auth_provider == "supabase", "env": ["AUTH_PROVIDER", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"],
         "note": "Switches sign-in to Supabase. Roles and organisations stay in BrandSure."},
    ]}
