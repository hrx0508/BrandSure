import base64
import hashlib
import hmac
import json
import time

import pytest

from app.core.errors import AppError
from app.services import document_extractor as ex
from app.services import gdocs, notify, supabase_auth


def _jwt(payload, secret="s3cret", alg="HS256"):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    head, body = b({"alg": alg, "typ": "JWT"}), b(payload)
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{head}.{body}.{sig}"


def test_supabase_jwt_verification():
    good = _jwt({"sub": "u-1", "aud": "authenticated", "exp": time.time() + 60})
    assert supabase_auth.verify_hs256(good, "s3cret")["sub"] == "u-1"
    assert supabase_auth.verify_hs256(good, "wrong") is None
    assert supabase_auth.verify_hs256(_jwt({"sub": "u", "aud": "authenticated", "exp": time.time() - 5}), "s3cret") is None
    assert supabase_auth.verify_hs256(_jwt({"sub": "u", "aud": "other", "exp": time.time() + 60}), "s3cret") is None
    assert supabase_auth.verify_hs256(_jwt({"sub": "u", "aud": "authenticated", "exp": time.time() + 60}, alg="none"), "s3cret") is None
    assert supabase_auth.verify_hs256("not.a.jwt", "s3cret") is None


def test_supabase_mode_uses_jwt_and_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "s.db"))
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "s3cret")
    from app.core import security
    from app.db.client import init_db
    from app.repositories import store
    init_db()
    store.insert("profiles", user_id="sb-user-1", organisation_id="org_demo", role="creator", display_name="Sam", email="sam@x.test", password_hash="")
    tok = _jwt({"sub": "sb-user-1", "aud": "authenticated", "exp": time.time() + 60})
    assert security.user_from_token(tok).role == "creator"
    with pytest.raises(AppError):  # valid Supabase user without a BrandSure profile
        security.user_from_token(_jwt({"sub": "unknown", "aud": "authenticated", "exp": time.time() + 60}))


def test_google_doc_url_parsing():
    assert gdocs.doc_id("https://docs.google.com/document/d/1AbCdEfGhIjK-lm_NOP/edit?usp=sharing") == "1AbCdEfGhIjK-lm_NOP"
    for bad in ("https://evil.example/document/d/1AbCdEfGhIjK", "http://docs.google.com/document/d/1AbCdEfGhIjK", "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjK"):
        with pytest.raises(AppError) as e:
            gdocs.doc_id(bad)
        assert e.value.code == "INVALID_URL"


def test_text_import_units_and_minimum():
    r = ex.from_text("The official company name is TechNova.\n\nNever write it as Tech Nova.\n")
    assert [u["ref"]["paragraph"] for u in r["units"]] == [1, 3]
    with pytest.raises(AppError) as e:
        ex.from_text("too short")
    assert e.value.code == "EMPTY_DOCUMENT"


class _Page:
    def __init__(self, text): self.t = text
    def get_text(self): return self.t


def _fake_fitz(monkeypatch, pages):
    import sys
    import types
    mod = types.ModuleType("fitz")
    mod.open = lambda **k: [_Page(t) for t in pages]
    monkeypatch.setitem(sys.modules, "fitz", mod)


def test_scanned_pdf_uses_ocr_when_available(monkeypatch):
    _fake_fitz(monkeypatch, ["", "Page two has real selectable text, enough to count as text."])
    monkeypatch.setattr(ex, "ocr_available", lambda: True)
    monkeypatch.setattr(ex, "_ocr_page", lambda page: "Scanned page text read by OCR, long enough to pass the minimum length check.")
    units, ocr, blank = ex._pdf(b"%PDF-fake")
    assert ocr == [1] and blank == 0 and units[0]["ref"] == {"page": 1, "ocr": True} and units[1]["ref"] == {"page": 2}


def test_scanned_pdf_without_ocr_explains_what_to_do(monkeypatch):
    _fake_fitz(monkeypatch, ["", ""])
    monkeypatch.setattr(ex, "ocr_available", lambda: False)
    with pytest.raises(AppError) as e:
        ex.extract("scan.pdf", b"%PDF-1.4 fake")
    assert e.value.code == "EMPTY_DOCUMENT" and "Tesseract" in e.value.message


def test_slack_is_a_no_op_without_webhook(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")
    assert notify.enabled() is False
    notify.notify("nothing happens")  # must not raise
