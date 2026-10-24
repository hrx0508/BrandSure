import pytest

from app.services.evidence_validator import AnalysisError, validate_findings
from tests.helpers import SAMPLE_DRAFT, kit_rules

RULES = kit_rules()
CLAIM = "India's No. 1 productivity platform"


def f(**kw):
    base = {"type": "unsupported_claim", "quoted_text": CLAIM, "explanation": "x", "severity": "medium",
            "verdict": "unverified", "source_ids": [], "source_quote": None}
    base.update(kw)
    return {"findings": [base]}


def one(raw):
    ok, rej = validate_findings(raw, SAMPLE_DRAFT, RULES)
    assert len(ok) == 1, rej
    return ok[0]


def test_malformed_structure_raises():
    with pytest.raises(AnalysisError):
        validate_findings({"nope": 1}, SAMPLE_DRAFT, RULES)


def test_schema_invalid_finding_rejected():
    ok, rej = validate_findings({"findings": [{"type": "bogus"}]}, SAMPLE_DRAFT, RULES)
    assert ok == [] and rej


def test_quote_not_in_draft_rejected():
    ok, rej = validate_findings(f(quoted_text="not in the draft"), SAMPLE_DRAFT, RULES)
    assert ok == [] and "not found" in rej[0]


def test_span_is_recomputed_not_trusted():
    r = one(f())
    assert SAMPLE_DRAFT[r["span"]["start"]:r["span"]["end"]] == CLAIM


def test_invented_source_id_never_verified():
    r = one(f(verdict="supported", source_ids=["made_up"], source_quote="whatever"))
    assert r["verdict"] == "unverified" and r["evidence_status"] == "invalid_citation" and r["source_refs"] == []


def test_supported_with_real_fact_is_verified():
    r = one(f(verdict="supported", source_ids=["R_fact"], source_quote="ranked No. 1 productivity platform in India"))
    assert r["verdict"] == "supported" and r["evidence_status"] == "verified"


def test_fake_quote_downgrades():
    r = one(f(verdict="supported", source_ids=["R_fact"], source_quote="TechNova is the undisputed leader"))
    assert r["verdict"] == "unverified" and r["evidence_status"] == "quote_invalid"


def test_irrelevant_source_downgrades():
    tone = next(x for x in RULES if x["type"] == "tone_guideline")
    r = one(f(verdict="supported", source_ids=[tone["id"]], source_quote="professional, friendly and clear"))
    assert r["verdict"] == "unverified" and r["evidence_status"] == "weak_support"


def test_unverified_requires_human_review():
    assert one(f())["requires_human_review"] is True
