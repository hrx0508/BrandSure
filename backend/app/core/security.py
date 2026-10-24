"""Identity, signed tokens, role checks and a small rate limiter.

Roles and organisation ALWAYS come from the database row of the authenticated user, never from the client.
To move to Supabase Auth later: verify the Supabase JWT in `user_from_token` and keep everything else.
"""
import base64
import hashlib
import hmac
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Depends, Header

from app.core.config import get_settings
from app.core.errors import AppError
from app.repositories import store


@dataclass(frozen=True)
class User:
    id: str
    organisation_id: str
    role: str
    display_name: str
    email: str = ""


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _sign(body: str) -> str:
    return _b64(hmac.new(get_settings().secret_key.encode(), body.encode(), hashlib.sha256).digest())


def make_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + get_settings().token_ttl_hours * 3600}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body)}"


def read_token(token: str):
    """Returns the user id, or None if the token is malformed, tampered with or expired."""
    try:
        body, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(body)):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return payload["sub"] if payload["exp"] > time.time() else None
    except (ValueError, KeyError, TypeError):
        return None


def user_from_token(token: str) -> User:
    if get_settings().auth_provider == "supabase":
        from app.services import supabase_auth
        uid = supabase_auth.verify_access_token(token)
    else:
        uid = read_token(token)
    p = store.fetch_one("SELECT * FROM profiles WHERE user_id = ?", (uid,)) if uid else None
    if not p:
        raise AppError(401, "UNAUTHENTICATED", "Your session has expired. Sign in again.")  # also: signed in but no profile yet
    return User(p["user_id"], p["organisation_id"], p["role"], p["display_name"], p["email"])


def current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Sign in to continue.")
    return user_from_token(authorization[7:].strip())


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN", f"This action needs the {' or '.join(roles)} role.")
        return user

    return dep


_hits: dict = defaultdict(deque)


def rate_limit(key: str, limit: int, window: int = 60) -> None:
    """Simple in-memory limiter (per process). Use a shared store if you run several workers."""
    q, t = _hits[key], time.time()
    while q and q[0] < t - window:
        q.popleft()
    if len(q) >= limit:
        raise AppError(429, "RATE_LIMITED", "Too many requests. Wait a moment and try again.")
    q.append(t)
