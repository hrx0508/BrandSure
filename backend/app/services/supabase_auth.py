"""Supabase Auth integration (AUTH_PROVIDER=supabase). Fill the SUPABASE_* values in backend/.env.

* Tokens are checked locally with the project's JWT secret (HS256) when SUPABASE_JWT_SECRET is set; otherwise by asking
  Supabase (GET /auth/v1/user, cached for 60 s), which also works for projects that use asymmetric signing keys.
* Application roles and organisations stay in our `profiles` table; Supabase only proves who the person is.
"""
import base64
import hashlib
import hmac
import json
import time

from app.core.config import get_settings
from app.core.errors import AppError

_cache: dict = {}


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def verify_hs256(token: str, secret: str, audience: str = "authenticated"):
    """Returns the payload of a valid, unexpired HS256 token for this audience, else None."""
    try:
        head, body, sig = token.split(".")
        if json.loads(_unb64(head)).get("alg") != "HS256":
            return None
        want = hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(want, _unb64(sig)):
            return None
        payload = json.loads(_unb64(body))
        aud = payload.get("aud")
        if payload["exp"] <= time.time() or (aud != audience and audience not in (aud or [])):
            return None
        return payload
    except (ValueError, KeyError, TypeError):
        return None


def _need(*names):
    s = get_settings()
    missing = [n for n in names if not getattr(s, n)]
    if missing:
        raise AppError(500, "AUTH_NOT_CONFIGURED", "Supabase Auth is not configured on the server (see docs/INTEGRATIONS.md).")
    return s


def _call(method: str, path: str, key: str, bearer: str | None = None, json_body=None):
    s = get_settings()
    import httpx
    headers = {"apikey": key, "Authorization": f"Bearer {bearer or key}", "Content-Type": "application/json"}
    try:
        return httpx.request(method, f"{s.supabase_url}{path}", headers=headers, json=json_body, timeout=15)
    except httpx.HTTPError as e:
        raise AppError(502, "AUTH_PROVIDER_ERROR", "The sign-in service could not be reached.") from e


def verify_access_token(token: str):
    """Returns the Supabase user id for a valid access token, else None."""
    s = get_settings()
    if s.supabase_jwt_secret:
        p = verify_hs256(token, s.supabase_jwt_secret)
        return p.get("sub") if p else None
    _need("supabase_url", "supabase_anon_key")
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    r = _call("GET", "/auth/v1/user", s.supabase_anon_key, bearer=token)
    uid = r.json().get("id") if r.status_code == 200 else None
    _cache[key] = (time.time() + 60, uid)
    return uid


def _session(r):
    if r.status_code != 200:
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    d = r.json()
    return {"access_token": d["access_token"], "refresh_token": d.get("refresh_token"), "user_id": d["user"]["id"]}


def password_login(email: str, password: str) -> dict:
    s = _need("supabase_url", "supabase_anon_key")
    return _session(_call("POST", "/auth/v1/token?grant_type=password", s.supabase_anon_key, json_body={"email": email, "password": password}))


def refresh(refresh_token: str) -> dict:
    s = _need("supabase_url", "supabase_anon_key")
    return _session(_call("POST", "/auth/v1/token?grant_type=refresh_token", s.supabase_anon_key, json_body={"refresh_token": refresh_token}))


def signup(email: str, password: str) -> str:
    s = _need("supabase_url", "supabase_anon_key")
    r = _call("POST", "/auth/v1/signup", s.supabase_anon_key, json_body={"email": email, "password": password})
    if r.status_code not in (200, 201):
        raise AppError(400, "SIGNUP_FAILED", "Could not create this account. The email may already be registered.")
    d = r.json()
    return (d.get("user") or d)["id"]


def admin_create_user(email: str, password: str) -> str:
    s = _need("supabase_url", "supabase_service_key")
    r = _call("POST", "/auth/v1/admin/users", s.supabase_service_key, json_body={"email": email, "password": password, "email_confirm": True})
    if r.status_code not in (200, 201):
        raise AppError(400, "SIGNUP_FAILED", "Could not create this account. The email may already be registered.")
    return r.json()["id"]
