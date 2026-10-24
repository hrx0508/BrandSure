import io
import os
import tempfile

import pytest

from app.core.passwords import hash_password, verify_password
from app.services import rule_engine as re_
from tests.helpers import kit_rules


def _png(color, size=(60, 60)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


def test_contrast_ratio_known_values():
    assert round(re_.contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0
    assert re_.contrast_ratio("#FFFFFF", "#F4B6C2") < 2.5


def test_candidates_include_palette_and_accessibility():
    types = {r["type"] for r in kit_rules()}
    assert {"palette", "accessibility"} <= types
    acc = next(r for r in kit_rules() if r["type"] == "accessibility")
    assert acc["params"] == {"require_alt": True, "min_contrast": 4.5}


def test_image_checks_alt_contrast_palette():
    from app.services.image_checker import analyze_image
    info = analyze_image(_png((230, 30, 30)))  # saturated red: not in the approved palette
    assert info["dominant"][0]["share"] > 0.9 and info["thumb"].startswith("data:image/jpeg")
    im = {"id": "i1", "filename": "hero.png", "alt_text": "", "text_color": "#FFFFFF", "bg_color": "#F4B6C2", "dominant": info["dominant"]}
    types = sorted(f["type"] for f in re_.check_images([im], kit_rules()))
    assert types == ["low_contrast", "missing_alt", "visual_palette"]
    ok = {**im, "alt_text": "Red banner", "text_color": "#111111", "dominant": [{"hex": "#5B35F5", "share": 1.0}]}
    assert re_.check_images([ok], kit_rules()) == []


def test_neutral_colours_not_judged_against_palette():
    im = {"id": "i", "filename": "g.png", "alt_text": "x", "dominant": [{"hex": "#808080", "share": 1.0}]}
    assert re_.check_images([im], kit_rules()) == []


def test_bad_image_rejected():
    from app.core.errors import AppError
    from app.services.image_checker import analyze_image
    with pytest.raises(AppError) as e:
        analyze_image(b"not an image")
    assert e.value.code == "UNSUPPORTED_IMAGE"


def test_password_hash_roundtrip():
    h = hash_password("correct horse")
    assert verify_password("correct horse", h) and not verify_password("wrong", h) and not verify_password("x", "garbage")


def test_token_roundtrip_tamper_and_expiry(monkeypatch):
    from app.core import security
    t = security.make_token("u1")
    assert security.read_token(t) == "u1"
    body, sig = t.split(".")
    assert security.read_token(body + "." + sig[:-2] + "AA") is None
    assert security.read_token("garbage") is None
    monkeypatch.setenv("TOKEN_TTL_HOURS", "-1")
    assert security.read_token(security.make_token("u1")) is None


def test_insights_from_events(monkeypatch):
    monkeypatch.setenv("DB_PATH", os.path.join(tempfile.mkdtemp(), "i.db"))
    monkeypatch.setenv("DEMO_CONTENT", "false")  # start from an empty organisation
    from app.db.client import init_db
    from app.repositories import store
    from app.services.insights import build_insights
    init_db()
    assert build_insights("org_demo")["insufficient_data"] is True
    for i in range(4):  # same rule shown in 4 different reviews, dismissed 3 times
        store.audit("org_demo", "u_creator", "review.analyzed", f"rev{i}", version=1, by_type={"tone_mismatch": 1}, by_rule={"Tone": 1})
    store.audit("org_demo", "u_creator", "review.analyzed", "rev0", version=1, by_type={"tone_mismatch": 1}, by_rule={"Tone": 1})  # re-run: not double counted
    for _ in range(3):
        store.audit("org_demo", "u_creator", "finding.dismissed", "rev0", rule="Tone", type="tone_mismatch")
    r = build_insights("org_demo")
    assert r["versions_analyzed"] == 4 and r["by_type"] == [{"type": "tone_mismatch", "count": 4}]
    rule = r["rules"][0]
    assert rule["shown"] == 4 and rule["dismiss_rate"] == 0.75 and rule["possibly_unclear"] is True


def test_env_file_parsing_handles_comments_quotes_and_bom():
    from app.core.config import parse_env_text
    text = "\ufeff# header\nAPP_ENV=development            # note\nSEED_DEMO=true  # creates demo\nEVAL_DATE=      # optional\nSECRET_KEY=\"a # b\"\nLLM_API_KEY=\nDB_PATH=brandsure.db\nURL=https://x.test/a#frag\n"
    env = parse_env_text(text)
    assert env["APP_ENV"] == "development" and env["SEED_DEMO"] == "true" and env["EVAL_DATE"] == "" and env["SECRET_KEY"] == "a # b"
    assert env["LLM_API_KEY"] == "" and env["DB_PATH"] == "brandsure.db" and env["URL"] == "https://x.test/a#frag"


def test_template_env_file_loads_cleanly():
    """The shipped .env.example must produce sane values when copied to .env as-is."""
    from pathlib import Path
    from app.core.config import parse_env_text
    env = parse_env_text((Path(__file__).resolve().parents[1] / ".env.example").read_text())
    assert env["APP_ENV"] == "development" and env["SEED_DEMO"] == "true" and env["DEMO_LOGIN"] == "true"
    assert env["EVAL_DATE"] == "" and env["SUPABASE_SERVICE_ROLE_KEY"] == "" and env["AUTH_PROVIDER"] == "local"
    assert all("#" not in v for v in env.values() if not v.startswith("http"))
