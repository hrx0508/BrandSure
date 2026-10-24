import re

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.passwords import hash_password, verify_password
from app.core.security import User, current_user, make_token, rate_limit, require_role
from app.repositories import store
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, UserCreate

router = APIRouter(tags=["auth"])
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _supabase() -> bool:
    return get_settings().auth_provider == "supabase"


def _public(p: dict) -> dict:
    return {"id": p["user_id"], "role": p["role"], "display_name": p["display_name"],
            "email": p["email"], "organisation_id": p["organisation_id"]}


def _email(raw: str) -> str:
    e = raw.strip().lower()
    if not EMAIL.match(e):
        raise AppError(422, "VALIDATION_ERROR", "Enter a valid email address.")
    return e


def _profile(uid: str) -> dict:
    p = store.fetch_one("SELECT * FROM profiles WHERE user_id = ?", (uid,))
    if not p:
        raise AppError(403, "NO_PROFILE", "Your account is not linked to an organisation yet. Ask an admin to add you.")
    return p


@router.post("/auth/login")
def login(body: LoginIn):
    email = _email(body.email)
    rate_limit(f"login:{email}", 10)
    if _supabase():
        from app.services import supabase_auth
        s = supabase_auth.password_login(email, body.password)
        return {"token": s["access_token"], "refresh_token": s["refresh_token"], "user": _public(_profile(s["user_id"]))}
    p = store.fetch_one("SELECT * FROM profiles WHERE email = ?", (email,))
    if not p or not verify_password(body.password, p["password_hash"]):
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    return {"token": make_token(p["user_id"]), "user": _public(p)}


@router.post("/auth/refresh")
def refresh(body: RefreshIn):
    if not _supabase():
        raise AppError(400, "NOT_SUPPORTED", "Token refresh is only used with Supabase Auth.")
    from app.services import supabase_auth
    s = supabase_auth.refresh(body.refresh_token)
    return {"token": s["access_token"], "refresh_token": s["refresh_token"]}


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn):
    if not get_settings().allow_registration:
        raise AppError(403, "REGISTRATION_DISABLED", "Registration is disabled. Ask an admin to create your account.")
    email = _email(body.email)
    rate_limit(f"register:{email}", 5)
    if store.fetch_one("SELECT 1 AS x FROM profiles WHERE email = ?", (email,)):
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists.")
    org = store.new_id("org")
    if _supabase():
        from app.services import supabase_auth
        uid, pw_hash = supabase_auth.signup(email, body.password), ""
    else:
        uid, pw_hash = store.new_id("usr"), hash_password(body.password)
    store.insert("organisations", id=org, name=body.organisation_name.strip(), created_at=store.now())
    store.insert("profiles", user_id=uid, organisation_id=org, role="admin", display_name=body.display_name.strip(), email=email, password_hash=pw_hash)
    store.audit(org, uid, "org.created", org)
    out = {"user": _public(_profile(uid)), "token": None}
    if _supabase():
        try:
            s = supabase_auth.password_login(email, body.password)
            out.update(token=s["access_token"], refresh_token=s["refresh_token"])
        except AppError:  # e-mail confirmation is switched on in Supabase
            out["message"] = "Check your email to confirm your address, then sign in."
    else:
        out["token"] = make_token(uid)
    return out


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "role": user.role, "display_name": user.display_name, "email": user.email,
            "organisation_id": user.organisation_id}


@router.get("/users")
def list_users(user: User = Depends(require_role("admin"))):
    rows = store.fetch_all("SELECT * FROM profiles WHERE organisation_id = ? ORDER BY role, display_name", (user.organisation_id,))
    return {"users": [_public(r) for r in rows]}


@router.get("/reviewers")
def list_reviewers(user: User = Depends(current_user)):
    """Reviewers a creator can send a post to (names only)."""
    rows = store.fetch_all("SELECT user_id, display_name FROM profiles WHERE organisation_id = ? AND role = 'reviewer' ORDER BY display_name", (user.organisation_id,))
    return {"reviewers": [{"id": r["user_id"], "display_name": r["display_name"]} for r in rows]}


@router.post("/users", status_code=201)
def create_user(body: UserCreate, user: User = Depends(require_role("admin"))):
    email = _email(body.email)
    if store.fetch_one("SELECT 1 AS x FROM profiles WHERE email = ?", (email,)):
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists.")
    if _supabase():
        from app.services import supabase_auth
        uid, pw_hash = supabase_auth.admin_create_user(email, body.password), ""
    else:
        uid, pw_hash = store.new_id("usr"), hash_password(body.password)
    store.insert("profiles", user_id=uid, organisation_id=user.organisation_id, role=body.role,
                 display_name=body.display_name.strip(), email=email, password_hash=pw_hash)
    store.audit(user.organisation_id, user.id, "user.created", uid, role=body.role)
    return _public(_profile(uid))
