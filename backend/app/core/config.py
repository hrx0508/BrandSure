"""Settings read from environment (and backend/.env) at call time."""
import os
import re
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def parse_env_text(text: str) -> dict:
    """Parses KEY=value lines. Supports inline comments (`KEY=value   # note`), quoted values and a UTF-8 BOM."""
    out = {}
    for line in text.lstrip("\ufeff").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value[:1] in ("'", '"'):
            end = value.find(value[0], 1)
            value = value[1:end] if end > 0 else value[1:]
        elif value.startswith("#"):
            value = ""
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        out[key.strip()] = value
    return out


def _load_env_file() -> None:
    path = BASE_DIR / ".env"
    if path.exists():
        for k, v in parse_env_text(path.read_text(encoding="utf-8-sig")).items():
            os.environ.setdefault(k, v)


_load_env_file()


@dataclass(frozen=True)
class Settings:
    app_env: str
    frontend_origins: list
    db_path: str
    max_upload_mb: int
    llm_api_key: str
    llm_model: str
    llm_url: str
    eval_date: str
    secret_key: str
    token_ttl_hours: int
    seed_demo: bool
    allow_registration: bool
    auth_provider: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    supabase_jwt_secret: str
    slack_webhook_url: str
    ocr_enabled: bool
    ocr_lang: str
    demo_login: bool
    demo_content: bool
    min_text_chars: int = 50

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def get_settings() -> Settings:
    e = os.environ.get
    env = e("APP_ENV", "development")
    seed = e("SEED_DEMO", "true").lower() == "true"
    return Settings(
        app_env=env,
        frontend_origins=[o.strip() for o in e("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if o.strip()],
        db_path=e("DB_PATH", str(BASE_DIR / "brandsure.db")),
        max_upload_mb=int(e("MAX_UPLOAD_MB", "10")),
        llm_api_key=e("LLM_API_KEY", ""),
        llm_model=e("LLM_MODEL", "claude-sonnet-5-5"),
        llm_url=e("LLM_URL", "https://api.anthropic.com/v1/messages"),
        eval_date=e("EVAL_DATE", "") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", e("EVAL_DATE", "").strip()) else "",
        secret_key=e("SECRET_KEY", "dev-insecure-secret-change-me"),
        token_ttl_hours=int(e("TOKEN_TTL_HOURS", "12")),
        seed_demo=e("SEED_DEMO", "true").lower() == "true",
        allow_registration=e("ALLOW_REGISTRATION", "true").lower() == "true",
        auth_provider=e("AUTH_PROVIDER", "local").lower(),
        supabase_url=e("SUPABASE_URL", "").rstrip("/"),
        supabase_anon_key=e("SUPABASE_ANON_KEY", ""),
        supabase_service_key=e("SUPABASE_SERVICE_ROLE_KEY", ""),
        supabase_jwt_secret=e("SUPABASE_JWT_SECRET", ""),
        slack_webhook_url=e("SLACK_WEBHOOK_URL", ""),
        ocr_enabled=e("OCR_ENABLED", "true").lower() == "true",
        ocr_lang=e("OCR_LANG", "eng"),
        demo_login=e("DEMO_LOGIN", "true" if env == "development" else "false").lower() == "true",
        demo_content=e("DEMO_CONTENT", "true" if seed else "false").lower() == "true",
    )
