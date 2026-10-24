from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import approvals, auth, brand_kits, demo, insights, integrations, reviews, tasks
from app.core import errors
from app.core.config import get_settings
from app.db.client import init_db
from app.services import llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.app_env == "production" and s.secret_key == "dev-insecure-secret-change-me":
        raise RuntimeError("Set SECRET_KEY to a long random value in production.")
    init_db()
    yield


app = FastAPI(title="BrandSure API", version="1.2.0", lifespan=lifespan)
app.middleware("http")(errors.request_id_middleware)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().frontend_origins, allow_methods=["*"], allow_headers=["*"])
errors.install(app)

api = APIRouter(prefix="/api/v1")


@api.get("/health")
def health():
    s = get_settings()
    out = {"status": "ok", "ai_mode": "llm" if llm.configured() else "offline_heuristic",
           "ai_notice": ("Extracted text and drafts are sent to an external AI service for analysis." if llm.configured()
                         else "AI service is off. Checks run on this server only; nothing is sent to an external service."),
           "registration": s.allow_registration, "ai_enabled": llm.configured(), "auth_provider": s.auth_provider}
    out["demo_login"] = s.demo_login and s.auth_provider == "local"  # shows the one-click demo buttons
    return out


for mod in (auth, brand_kits, reviews, approvals, insights, tasks, integrations, demo):
    api.include_router(mod.router)
app.include_router(api)
