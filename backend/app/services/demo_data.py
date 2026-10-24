"""Sample content for the one-click demo: a live TechNova Brand Kit; a draft (creator submits it), a submitted post (reviewer starts the review)
and a post the reviewer already sent back with flagged items (creator fixes it).
Everything is fictional. Created through the same code paths as real work, so Insights and history show real events."""
from collections import Counter
from datetime import date

from app.repositories import store
from app.services import review_service
from app.services.candidate_extractor import extract_candidates
from app.services.rule_engine import today_ist

DEMO_ORG = "org_demo"
GUIDELINES = [
    "TechNova Brand Guidelines",
    "The official company name is TechNova. Never write it as \u201cTech Nova\u201d or \u201cTechnova\u201d.",
    "Our tone is professional, friendly and clear; avoid exaggerated claims.",
    "The current promotion is a 20% discount, valid through 15 October 2026.",
    "Ranking claims such as \u201cNo. 1\u201d require approved evidence before publication.",
    "Never use the word \u201ccheap\u201d in public content.",
    "The approved colour palette is #5B35F5, #1FBF8A, #14112B and #FFFFFF.",
    "Every image needs alt text, and text must meet a contrast ratio of at least 4.5:1.",
]
FACT = "TechNova was ranked No. 1 productivity platform in Asia by Example Research, 2026."
DRAFT_A = "Tech Nova is India's No. 1 productivity platform.\nGet 20% off until October 30, 2026!"
DRAFT_B = "Tech Nova makes planning easy. A cheap, revolutionary way to stay organised!"


DRAFT_C = "Tech Nova: a cheap, revolutionary planner! We are the best-in-class app for your team."


def _post(kit_id, kit_version_id, title, content, status):
    """status: draft | submitted (reviewer has not started) | sent_back (reviewer reviewed, flagged items, returned it)."""
    rid, vid = store.new_id("rev"), store.new_id("rv")
    store.insert("reviews", id=rid, organisation_id=DEMO_ORG, kit_id=kit_id, kit_version_id=kit_version_id, title=title, content_type="social",
                 status="draft", created_by="u_creator", created_at=store.now(), updated_at=store.now())
    store.insert("review_versions", id=vid, review_id=rid, version_number=1, content=content, created_by="u_creator", created_at=store.now())
    store.audit(DEMO_ORG, "u_creator", "review.created", rid, kit_version_id=kit_version_id)
    if status == "draft":
        return rid
    store.update("reviews", rid, status="in_review", reviewer_id="u_reviewer", round=1, updated_at=store.now())
    store.audit(DEMO_ORG, "u_creator", "review.requested", rid, version=1, reviewer="u_reviewer", round=1)
    if status == "submitted":
        return rid
    # the reviewer starts the review, flags the real problems, dismisses one, adds a suggestion and sends it back
    from app.api.v1.brand_kits import load_rules
    found, meta = review_service.run_analysis(content, load_rules(kit_version_id), today_ist(), [])
    review_service.persist_findings(vid, found)
    store.update("review_versions", vid, analyzed_at=store.now(), analysis_json=meta)
    by_type = dict(Counter(f["type"] for f in found))
    by_rule = dict(Counter((f["source_refs"][0]["title"] if f.get("source_refs") else f["type"]) for f in found))
    store.audit(DEMO_ORG, "u_reviewer", "review.analyzed", rid, version=1, findings=len(found), ai_mode=meta["ai_mode"], by_type=by_type, by_rule=by_rule)
    dismissed_one = False
    for f in store.fetch_all("SELECT * FROM findings WHERE review_version_id = ? ORDER BY position", (vid,)):
        rule = (f["source_refs"] or [{}])[0].get("title") or f["type"]
        status_ = "dismissed" if (f["type"] == "tone_mismatch" and not dismissed_one) else "flagged"
        dismissed_one = dismissed_one or status_ == "dismissed"
        store.update("findings", f["id"], status=status_)
        store.audit(DEMO_ORG, "u_reviewer", f"finding.{status_}", rid, finding=f["id"], type=f["type"], rule=rule)
    start = content.find("a cheap, revolutionary planner")
    if start >= 0:
        store.insert("findings", id=store.new_id("fnd"), review_version_id=vid, type="reviewer_suggestion", severity="medium", verdict=None,
                     span_json={"start": start, "end": start + len("a cheap, revolutionary planner")}, quoted_text="a cheap, revolutionary planner",
                     explanation="Say what the product does, plainly.", source_ids_json=[], source_refs_json=[], evidence_status="reviewer",
                     suggested_fix="a simple planner", replacement="a simple planner", origin="reviewer", requires_human_review=0, uncertainty=None,
                     position=1000, status="flagged", meta_json={"author": "Riya (Reviewer)"})
        store.audit(DEMO_ORG, "u_reviewer", "review.suggested", rid, version=1)
    reason = "Please fix the flagged items: the name, the banned word and the unsupported ranking claim."
    store.insert("approval_events", id=store.new_id("apr"), review_id=rid, version_id=vid, reviewer_id="u_reviewer", decision="request_changes",
                 reason=reason, created_at=store.now())
    store.update("reviews", rid, status="changes_requested", updated_at=store.now())
    store.audit(DEMO_ORG, "u_reviewer", "review.changes_requested", rid, version=1, override=False, reason=reason)
    return rid


def seed_content() -> None:
    if not store.fetch_one("SELECT 1 AS x FROM organisations WHERE id = ?", (DEMO_ORG,)):
        return  # the demo organisation does not exist in this database
    if store.fetch_one("SELECT 1 AS x FROM brand_kits WHERE organisation_id = ?", (DEMO_ORG,)):
        return
    units = [{"ref": {"paragraph": i + 1}, "text": t} for i, t in enumerate(GUIDELINES)]
    cands, _, _ = extract_candidates(units)
    kit_id, vid = store.new_id("kit"), store.new_id("ver")
    store.insert("brand_kits", id=kit_id, organisation_id=DEMO_ORG, name="TechNova Brand Kit (demo)", active_version_id=None,
                 created_by="u_admin", created_at=store.now())
    store.insert("brand_kit_versions", id=vid, kit_id=kit_id, version_number=1, status="confirmed", confirmed_by="u_admin",
                 confirmed_at=store.now(), created_at=store.now())
    for c in cands:
        store.insert("brand_rules", id=store.new_id("rule"), version_id=vid, type=c["type"], title=c["title"], content=c["content"],
                     severity=c["severity"], valid_from=None, valid_until=c.get("valid_until"), params_json=c["params"],
                     source_json={**c["source"], "quote_verified": True})
    store.insert("brand_rules", id=store.new_id("rule"), version_id=vid, type="fact", title="Approved fact: ranking", content=FACT,
                 severity="low", valid_from=None, valid_until=None, params_json={}, source_json=None)
    store.update("brand_kits", kit_id, active_version_id=vid, published_at=store.now(), published_by="u_admin")
    store.audit(DEMO_ORG, "u_admin", "kit.confirmed", kit_id, version=1, rules=len(cands) + 1)
    store.audit(DEMO_ORG, "u_admin", "kit.published", kit_id)
    _post(kit_id, vid, "Launch post (draft)", DRAFT_A, "draft")                 # creator: finish and submit
    _post(kit_id, vid, "Weekly tips post", DRAFT_B, "submitted")                # reviewer: start the review
    _post(kit_id, vid, "Team planner post", DRAFT_C, "sent_back")               # creator: fix what was flagged


def reset_content() -> None:
    """Delete everything in the demo organisation (not the demo accounts) and load the sample content again."""
    q = lambda sql: store.execute(sql, (DEMO_ORG,))
    rv = "SELECT id FROM review_versions WHERE review_id IN (SELECT id FROM reviews WHERE organisation_id = ?)"
    q(f"DELETE FROM findings WHERE review_version_id IN ({rv})")
    q(f"DELETE FROM review_images WHERE review_version_id IN ({rv})")
    q("DELETE FROM review_versions WHERE review_id IN (SELECT id FROM reviews WHERE organisation_id = ?)")
    q("DELETE FROM review_comments WHERE review_id IN (SELECT id FROM reviews WHERE organisation_id = ?)")
    q("DELETE FROM approval_events WHERE review_id IN (SELECT id FROM reviews WHERE organisation_id = ?)")
    q("DELETE FROM reviews WHERE organisation_id = ?")
    q("UPDATE brand_kits SET active_version_id = NULL WHERE organisation_id = ?")
    q("DELETE FROM brand_rules WHERE version_id IN (SELECT v.id FROM brand_kit_versions v JOIN brand_kits k ON k.id = v.kit_id WHERE k.organisation_id = ?)")
    q("DELETE FROM brand_kit_versions WHERE kit_id IN (SELECT id FROM brand_kits WHERE organisation_id = ?)")
    q("DELETE FROM documents WHERE organisation_id = ?")
    q("DELETE FROM brand_kits WHERE organisation_id = ?")
    q("DELETE FROM audit_events WHERE organisation_id = ?")
    seed_content()
