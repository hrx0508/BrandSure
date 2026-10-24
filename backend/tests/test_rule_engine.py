from datetime import date

from tests.helpers import SAMPLE_DRAFT, kit_rules
from app.services import rule_engine as re_


def rules():
    return [r for r in kit_rules() if r["id"] != "R_fact"]


def types(findings):
    return [f["type"] for f in findings]


def test_preferred_term_flags_tech_nova_with_span():
    f = [x for x in re_.check_terms(SAMPLE_DRAFT, rules()) if x["type"] == "terminology"]
    assert len(f) == 1 and f[0]["quoted_text"] == "Tech Nova" and f[0]["span"] == {"start": 0, "end": 9}
    assert f[0]["replacement"] == "TechNova"


def test_correct_spelling_is_not_flagged():
    assert re_.check_terms("TechNova ships today.", rules()) == []


def test_case_variants_flagged_but_no_substring_match():
    assert len(re_.check_terms("We love TECHNOVA and technova.", rules())) == 2
    assert re_.check_terms("Technovation week", rules()) == []


def test_banned_term_word_boundary():
    assert types(re_.check_terms("A cheap deal", rules())) == ["banned_term"]
    assert re_.check_terms("Cheaper? We did not say that word.", rules()) == []


def test_expiry_and_date_conflict_on_demo_draft():
    f = re_.check_expiry(SAMPLE_DRAFT, rules(), date(2026, 10, 20))
    assert sorted(types(f)) == ["date_conflict", "expired_offer"]
    conflict = next(x for x in f if x["type"] == "date_conflict")
    assert conflict["quoted_text"] == "October 30, 2026"


def test_valid_through_is_inclusive():
    d = "Enjoy 20% off, offer ends 15 October 2026."
    assert re_.check_expiry(d, rules(), date(2026, 10, 15)) == []
    assert types(re_.check_expiry(d, rules(), date(2026, 10, 16))) == ["expired_offer"]


def test_claim_detection_spans_phrase():
    c = re_.detect_claims(SAMPLE_DRAFT)
    assert c and c[0]["quoted_text"] == "India's No. 1 productivity platform"


def test_missing_disclaimer():
    r = rules() + [{"id": "D", "type": "required_disclaimer", "title": "d", "content": "x", "severity": "high",
                    "valid_until": None, "params": {"phrase": "T&Cs apply."}}]
    assert types(re_.check_disclaimers("Buy now", r)) == ["missing_disclaimer"]
    assert re_.check_disclaimers("Buy now. T&Cs  apply.", r) == []


def test_deterministic():
    a = re_.run_checks(SAMPLE_DRAFT, rules(), date(2026, 10, 20))
    assert a == re_.run_checks(SAMPLE_DRAFT, rules(), date(2026, 10, 20))
