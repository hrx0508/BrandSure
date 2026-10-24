"""Every AI finding is a proposal. Nothing is displayed until it passes these checks."""
from pydantic import ValidationError

from app.schemas.review import RawFinding
from app.services.text_utils import locate, norm, tokens


class AnalysisError(Exception):
    pass


def _source_texts(rule):
    texts = [rule["content"]]
    q = (rule.get("source") or {}).get("quote")
    if q:
        texts.append(q)
    return texts


def validate_findings(raw, draft, rules):
    """raw: parsed AI output (dict with 'findings'). Returns (validated, rejected_reasons)."""
    if not isinstance(raw, dict) or not isinstance(raw.get("findings"), list):
        raise AnalysisError("AI output did not match the required structure.")
    by_id = {r["id"]: r for r in rules}
    ok, rejected = [], []
    for i, item in enumerate(raw["findings"]):
        try:
            f = RawFinding.model_validate(item)
        except ValidationError:
            rejected.append(f"#{i}: schema invalid")
            continue
        span = locate(draft, f.quoted_text)
        if not span:
            rejected.append(f"#{i}: quoted text not found in this draft version")
            continue
        valid = [s for s in dict.fromkeys(f.source_ids) if s in by_id]
        invalid = [s for s in dict.fromkeys(f.source_ids) if s not in by_id]
        quote_ok = None
        if f.source_quote:
            nq = norm(f.source_quote)
            quote_ok = any(nq and nq in norm(t) for s in valid for t in _source_texts(by_id[s]))
        qt = tokens(f.quoted_text)
        relevant = any(qt and len(qt & tokens(by_id[s]["content"])) / len(qt) >= 0.5 for s in valid)  # at least half the claim's words appear in the source
        verdict, status = f.verdict, "not_found"
        if verdict in ("supported", "contradicted"):
            if valid and quote_ok and relevant:
                status = "verified"
            else:  # cannot prove it -> downgrade, never show as verified
                verdict = "unverified"
                status = ("invalid_citation" if invalid and not valid else "quote_invalid" if f.source_quote and not quote_ok
                          else "weak_support" if valid else "not_found")
        elif verdict == "unverified":
            status = "not_found"
        elif valid and quote_ok is not False:
            status = "verified"
        elif invalid and not valid:
            status = "invalid_citation"
        elif quote_ok is False:
            status = "quote_invalid"
        refs = [{"id": s, "title": by_id[s]["title"], "type": by_id[s]["type"],
                 "quote": f.source_quote if quote_ok else by_id[s]["content"][:200]} for s in valid]
        ok.append({"type": f.type, "severity": f.severity, "verdict": verdict,
                   "span": {"start": span[0], "end": span[1]}, "quoted_text": draft[span[0]:span[1]],
                   "explanation": f.explanation, "source_ids": valid, "source_refs": refs,
                   "evidence_status": status, "suggested_fix": f.suggested_fix, "replacement": f.replacement,
                   "uncertainty": f.uncertainty, "origin": "ai",
                   "requires_human_review": verdict != "supported" or f.severity == "high" or status != "verified"})
    return ok, rejected
