from tests.helpers import GUIDELINE_PARAS
from app.services.candidate_extractor import extract_candidates

UNITS = [{"ref": {"paragraph": i + 1}, "text": t} for i, t in enumerate(GUIDELINE_PARAS)]


def test_extracts_expected_candidates_unapproved():
    c, w, mode = extract_candidates(UNITS)
    by = {}
    for x in c:
        by.setdefault(x["type"], []).append(x)
    assert by["preferred_term"][0]["params"]["preferred"] == "TechNova"
    assert "Tech Nova" in by["preferred_term"][0]["params"]["variants"]
    assert by["expiry"][0]["valid_until"] == "2026-10-15"
    assert by["banned_term"][0]["params"]["banned"] == "cheap"
    assert "claim_rule" in by and "tone_guideline" in by
    assert all(x["status"] == "pending_confirmation" and x["needs_human_confirmation"] for x in c)


def test_every_candidate_has_a_real_quote():
    c, _, _ = extract_candidates(UNITS)
    text = " ".join(GUIDELINE_PARAS)
    assert all(x["source"]["quote"] in text for x in c)


def test_ambiguous_date_needs_manual_entry():
    u = [{"ref": {"page": 1}, "text": "The offer of 10% is valid through 10/11/26."}]
    c, w, _ = extract_candidates(u)
    assert c[0]["valid_until"] is None and c[0]["confidence"] == "low" and w
