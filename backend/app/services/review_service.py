"""Orchestrates: deterministic checks -> AI analysis -> validation -> merged findings."""
from datetime import date

from app.repositories import store
from app.services import ai_analyzer, evidence_validator, llm, rule_engine


def _overlaps(a, b):
    return a and b and a["start"] < b["end"] and b["start"] < a["end"]


def run_analysis(draft: str, rules: list, today: date, images: list | None = None):
    det = rule_engine.run_checks(draft, rules, today) + rule_engine.check_images(images or [], rules)
    meta = {"evaluation_date": today.isoformat(), "ai_mode": None, "ai_error": None, "rejected": []}
    ai_findings = []
    try:
        raw, mode = ai_analyzer.analyze(draft, rules)
        meta["ai_mode"] = mode
        ai_findings, meta["rejected"] = evidence_validator.validate_findings(raw, draft, rules)
    except (llm.LLMError, evidence_validator.AnalysisError) as e:
        meta["ai_mode"], meta["ai_error"] = "failed", str(e)  # deterministic checks stay useful
    ai_findings = [f for f in ai_findings if not any(_overlaps(f["span"], d["span"]) for d in det)]
    ref = {r["id"]: r for r in rules}
    for d in det:
        d["source_refs"] = [{"id": s, "title": ref[s]["title"], "type": ref[s]["type"], "quote": ref[s]["content"][:200]}
                            for s in d["source_ids"] if s in ref]
    allf = sorted(det + ai_findings, key=lambda f: (f["span"]["start"] if f["span"] else -1))
    return allf, meta


def persist_findings(version_id: str, found: list) -> None:
    """Replace the automatic findings of a version (a reviewer's own suggestions are kept)."""
    store.execute("DELETE FROM findings WHERE review_version_id = ? AND origin != 'reviewer'", (version_id,))
    for i, f in enumerate(found):
        store.insert("findings", id=store.new_id("fnd"), review_version_id=version_id, type=f["type"], severity=f["severity"],
                     verdict=f["verdict"], span_json=f["span"], quoted_text=f["quoted_text"], explanation=f["explanation"],
                     source_ids_json=f["source_ids"], source_refs_json=f.get("source_refs", []), evidence_status=f["evidence_status"],
                     suggested_fix=f["suggested_fix"], replacement=f["replacement"], origin=f["origin"],
                     requires_human_review=int(f["requires_human_review"]), uncertainty=f["uncertainty"], position=i + 1,
                     meta_json=f.get("meta"))
