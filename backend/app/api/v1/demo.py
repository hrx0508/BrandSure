"""One-click demo access. Only available when DEMO_LOGIN=true (on by default in development, off in production)."""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import User, current_user, make_token
from app.repositories import store
from app.services import demo_data

router = APIRouter(tags=["demo"])
ACCOUNTS = {"admin": "u_admin", "creator": "u_creator", "reviewer": "u_reviewer"}


class DemoLoginIn(BaseModel):
    role: Literal["admin", "creator", "reviewer"]


def _enabled() -> None:
    s = get_settings()
    if not s.demo_login or s.auth_provider != "local":
        raise AppError(404, "NOT_FOUND", "Demo access is switched off.")


@router.post("/demo/login")
def demo_login(body: DemoLoginIn):
    _enabled()
    p = store.fetch_one("SELECT * FROM profiles WHERE user_id = ? AND organisation_id = ?", (ACCOUNTS[body.role], demo_data.DEMO_ORG))
    if not p:
        raise AppError(404, "NOT_FOUND", "The demo accounts have not been created. Set SEED_DEMO=true and restart.")
    return {"token": make_token(p["user_id"]), "user": {"id": p["user_id"], "role": p["role"], "display_name": p["display_name"],
                                                       "email": p["email"], "organisation_id": p["organisation_id"]}}


@router.post("/demo/reset")
def demo_reset(user: User = Depends(current_user)):
    _enabled()
    if user.organisation_id != demo_data.DEMO_ORG:
        raise AppError(403, "FORBIDDEN", "Only the demo organisation can be reset.")
    demo_data.reset_content()
    return {"reset": True}
