"""Everything the reviewer does: start the review (Brand Kit + AI checks), flag or dismiss findings,
suggest changes, edit the post, and decide (approve / send back / reject)."""
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends

from app.api.v1.brand_kits import load_rules
from app.api.v1.reviews import copy_images, findings_for, get_review, images_for, latest_version, name_of, touch
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import User, rate_limit, require_role
from app.repositories import store
from app.schemas.review import DecisionIn, ReviewerEditIn, StartReviewIn, SuggestionIn, TriageIn
from app.services import notify, review_service
from app.services.rule_engine import today_ist

router = APIRouter(tags=["approvals"])


def _reviewable(user: User, rid: str, version_number: int | None = None):
    r = get_review(user, rid)  # organisation-scoped
    if r["created_by"] == user.id:
        raise AppError(403, "FORBIDDEN", "You cannot review your own post.")
    if r["status"] != "in_review":
        raise AppError(409, "INVALID_STATE", "This post is not waiting for a reviewer.")
    if r["reviewer_id"] and r["reviewer_id"] != user.id:
        raise AppError(403, "FORBIDDEN", f"This post was sent to {name_of(r['reviewer_id'])}.")
    v = latest_version(rid)
    if version_number is not None and version_number != v["version_number"]:
        raise AppError(409, "STALE_VERSION", "A newer version exists. Review the latest version.")
    return r, v


def _rule_of(f: dict) -> str:
    return (f["source_refs"] or [{}])[0].get("title") or f["type"]


@router.post("/reviews/{rid}/start-review")
def start_review(rid: str, body: StartReviewIn | None = None, user: User = Depends(require_role("reviewer"))):
    """Runs the Brand Kit rules, image checks and (if configured) AI on the submitted version.
    Results are visible only to reviewers until a reviewer flags them for the creator."""
    rate_limit(f"review:{user.id}", 30)
    r, v = _reviewable(user, rid)
    if v["analyzed_at"] and not (body and body.rerun):
        raise AppError(409, "ALREADY_STARTED", "The review of this version has already started.")
    s = get_settings()
    today = date.fromisoformat(s.eval_date) if s.eval_date else today_ist()
    found, meta = review_service.run_analysis(v["content"], load_rules(r["kit_version_id"]), today, images_for(v["id"]))
    review_service.persist_findings(v["id"], found)  # a reviewer's own suggestions are kept on a re-run
    store.update("review_versions", v["id"], analyzed_at=store.now(), analysis_json=meta)
    touch(rid, reviewer_id=user.id)  # the first reviewer to start claims the post
    by_type = dict(Counter(f["type"] for f in found))
    by_rule = dict(Counter((f["source_refs"][0]["title"] if f.get("source_refs") else f["type"]) for f in found))
    store.audit(user.organisation_id, user.id, "review.analyzed", rid, version=v["version_number"], findings=len(found),
                ai_mode=meta["ai_mode"], by_type=by_type, by_rule=by_rule)
    return {"version_number": v["version_number"], "findings": findings_for(v["id"], "reviewer"), "analysis": meta}


def _set_status(user: User, rid: str, f: dict, status: str):
    store.update("findings", f["id"], status=status, final_text=None)
    store.audit(user.organisation_id, user.id, f"finding.{status}", rid, finding=f["id"], type=f["type"], rule=_rule_of(f))


@router.post("/reviews/{rid}/findings/{fid}/triage")
def triage(rid: str, fid: str, body: TriageIn, user: User = Depends(require_role("reviewer"))):
    """Reviewer decides whether a finding is a real problem (flag it for the creator) or not (dismiss it)."""
    _, v = _reviewable(user, rid)
    f = next((x for x in findings_for(v["id"], "reviewer") if x["id"] == fid), None)
    if not f:
        raise AppError(404, "NOT_FOUND", "Finding not found on the latest version.")
    status = {"flag": "flagged", "dismiss": "dismissed", "reopen": "open"}[body.action]
    _set_status(user, rid, f, status)
    touch(rid)
    return {"id": fid, "status": status}


@router.post("/reviews/{rid}/triage-all")
def triage_all(rid: str, user: User = Depends(require_role("reviewer"))):
    """Flag every finding that has not been triaged yet."""
    _, v = _reviewable(user, rid)
    n = 0
    for f in findings_for(v["id"], "reviewer"):
        if f["status"] == "open":
            _set_status(user, rid, f, "flagged")
            n += 1
    touch(rid)
    return {"flagged": n}


@router.post("/reviews/{rid}/suggestions", status_code=201)
def suggest(rid: str, body: SuggestionIn, user: User = Depends(require_role("reviewer"))):
    """Reviewer proposes replacement text for a selected part of the draft. It goes straight to the creator as a flag."""
    r, v = _reviewable(user, rid, body.version_number)
    if body.end > len(v["content"]) or body.start >= body.end:
        raise AppError(422, "VALIDATION_ERROR", "The selected text does not match this version of the draft.")
    fid = store.new_id("fnd")
    store.insert("findings", id=fid, review_version_id=v["id"], type="reviewer_suggestion", severity="medium", verdict=None,
                 span_json={"start": body.start, "end": body.end}, quoted_text=v["content"][body.start:body.end], explanation=body.note.strip(),
                 source_ids_json=[], source_refs_json=[], evidence_status="reviewer", suggested_fix=body.replacement, replacement=body.replacement,
                 origin="reviewer", requires_human_review=0, uncertainty=None, position=1000 + body.start, status="flagged", meta_json={"author": user.display_name})
    touch(rid, reviewer_id=user.id)
    store.audit(user.organisation_id, user.id, "review.suggested", rid, version=v["version_number"])
    return next(f for f in findings_for(v["id"], "reviewer") if f["id"] == fid)


@router.post("/reviews/{rid}/reviewer-edit", status_code=201)
def reviewer_edit(rid: str, body: ReviewerEditIn, user: User = Depends(require_role("reviewer"))):
    """Reviewer edits the post directly. It is saved as a new version and goes back to the creator."""
    r, v = _reviewable(user, rid, body.version_number)
    n = v["version_number"] + 1
    vid = store.new_id("rv")
    store.insert("review_versions", id=vid, review_id=rid, version_number=n, content=body.content, created_by=user.id, created_at=store.now())
    copy_images(v["id"], vid)
    store.insert("approval_events", id=store.new_id("apr"), review_id=rid, version_id=vid, reviewer_id=user.id, decision="edited",
                 reason=body.note.strip(), created_at=store.now())
    touch(rid, status="changes_requested", reviewer_id=r["reviewer_id"] or user.id)
    store.audit(user.organisation_id, user.id, "review.edited_by_reviewer", rid, version=n, reason=body.note.strip())
    notify.notify(f"BrandSure: {user.display_name} edited \u201c{r['title']}\u201d and sent it back to {name_of(r['created_by'])}.")
    return {"version_number": n, "status": "changes_requested"}


@router.post("/reviews/{rid}/decision")
def decide(rid: str, body: DecisionIn, user: User = Depends(require_role("reviewer"))):
    r, v = _reviewable(user, rid, body.version_number)
    reason = (body.reason or "").strip() or None
    if body.decision in ("request_changes", "reject") and not reason:
        raise AppError(422, "REASON_REQUIRED", "Explain what needs to change." if body.decision == "request_changes" else "Say why this post is rejected.")
    override = False
    if body.decision == "approve":
        if not v["analyzed_at"]:
            raise AppError(409, "REVIEW_NOT_STARTED", "Start the review first, so the post is checked against the Brand Kit before you approve it.")
        blocking = [f for f in findings_for(v["id"], "reviewer") if f["severity"] == "high" and f["status"] in ("open", "flagged")]
        override = bool(blocking)
        if override and not reason:
            raise AppError(422, "OVERRIDE_REASON_REQUIRED", f"{len(blocking)} high-severity finding(s) are still open or flagged. Give a reason to approve anyway.")
    store.insert("approval_events", id=store.new_id("apr"), review_id=rid, version_id=v["id"], reviewer_id=user.id,
                 decision=body.decision, reason=reason, created_at=store.now())
    status = {"approve": "approved", "request_changes": "changes_requested", "reject": "rejected"}[body.decision]
    touch(rid, status=status, reviewer_id=user.id)
    store.audit(user.organisation_id, user.id, f"review.{status}", rid, version=v["version_number"], override=override, reason=reason)
    label = {"approved": "approved and is ready to publish", "changes_requested": "sent back with flagged items", "rejected": "rejected"}[status]
    notify.notify(f"BrandSure: \u201c{r['title']}\u201d was {label} by {user.display_name}.")
    return {"status": status, "version_number": v["version_number"]}
