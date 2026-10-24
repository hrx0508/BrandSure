import re
from collections import Counter

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.v1.brand_kits import get_kit, kit_state
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import User, current_user, rate_limit, require_role
from app.repositories import store
from app.schemas.review import (CommentIn, FindingUpdate, GoogleDocReview, ImageUpdate, RequestReviewIn,
                                RevisionIn, ReviewCreate)
from app.services import document_extractor, gdocs, image_checker, llm, notify
from app.services.rule_engine import HEX_RE

router = APIRouter(tags=["reviews"])
EDITABLE = ("draft", "changes_requested")
MAX_IMAGES = 5


def scope(user: User):
    """Who can see which posts: creators their own; reviewers everything that has been sent to review; admins all."""
    if user.role == "creator":
        return " AND created_by = ?", [user.id]
    if user.role == "reviewer":
        return " AND status != 'draft'", []
    return "", []


def get_review(user: User, rid: str) -> dict:
    sql, params = scope(user)
    r = store.fetch_one(f"SELECT * FROM reviews WHERE id = ? AND organisation_id = ?{sql}", (rid, user.organisation_id, *params))
    if not r:
        raise AppError(404, "NOT_FOUND", "Review not found.")
    return r


def own_review(user: User, rid: str) -> dict:
    r = get_review(user, rid)
    if r["created_by"] != user.id:
        raise AppError(403, "FORBIDDEN", "Only the creator of this review can do that.")
    return r


def latest_version(rid: str) -> dict:
    return store.fetch_one("SELECT * FROM review_versions WHERE review_id = ? ORDER BY version_number DESC", (rid,))


def editable_latest(user: User, rid: str):
    r = own_review(user, rid)
    if r["status"] not in EDITABLE:
        raise AppError(409, "INVALID_STATE", "This post is locked while it is with the reviewer, approved, rejected or published.")
    return r, latest_version(rid)


CREATOR_VISIBLE = ("flagged", "accepted", "edited", "resolved")


def findings_for(version_id: str, role: str = "reviewer") -> list:
    """Creators only ever see findings the reviewer flagged (and what they did about them). Reviewers and admins see all."""
    rows = store.fetch_all("SELECT * FROM findings WHERE review_version_id = ? ORDER BY position, rowid", (version_id,))
    if role == "creator":
        rows = [f for f in rows if f["status"] in CREATOR_VISIBLE]
    for f in rows:
        f["requires_human_review"] = bool(f["requires_human_review"])
        f["source_refs"] = f["source_refs"] or []
        f["source_ids"] = f["source_ids"] or []
        f["meta"] = f.pop("meta") or {}
    return rows


def images_for(version_id: str) -> list:
    return store.fetch_all("SELECT * FROM review_images WHERE review_version_id = ? ORDER BY created_at, rowid", (version_id,))


def touch(rid: str, **vals):
    store.update("reviews", rid, updated_at=store.now(), **vals)


def name_of(uid: str | None) -> str | None:
    p = store.fetch_one("SELECT display_name FROM profiles WHERE user_id = ?", (uid,)) if uid else None
    return p["display_name"] if p else None


def _color(value, label):
    v = (value or "").strip()
    if v and not HEX_RE.match(v):
        raise AppError(422, "VALIDATION_ERROR", f"{label} must look like #RRGGBB.")
    return v.upper() or None


def _create_review(user: User, kit_id: str, title: str, content: str, content_type: str) -> dict:
    kit = get_kit(user, kit_id)
    state = kit_state(kit)
    if state == "inactive":
        raise AppError(409, "KIT_INACTIVE", "This Brand Kit has been deactivated by the admin.")
    if state != "live":
        raise AppError(409, "KIT_NOT_PUBLISHED", "The admin has not sent this Brand Kit to creators yet.")
    rid, vid = store.new_id("rev"), store.new_id("rv")
    store.insert("reviews", id=rid, organisation_id=user.organisation_id, kit_id=kit["id"], kit_version_id=kit["active_version_id"],
                 title=title, content_type=content_type, status="draft", created_by=user.id, created_at=store.now(), updated_at=store.now())
    store.insert("review_versions", id=vid, review_id=rid, version_number=1, content=content, created_by=user.id, created_at=store.now())
    store.audit(user.organisation_id, user.id, "review.created", rid, kit_version_id=kit["active_version_id"])
    return {"id": rid, "version_number": 1}


@router.get("/overview")
def overview(user: User = Depends(current_user)):
    sql, params = scope(user)
    rows = store.fetch_all(f"SELECT status, COUNT(*) AS n FROM reviews WHERE organisation_id = ?{sql} GROUP BY status", (user.organisation_id, *params))
    kits = store.fetch_all("SELECT * FROM brand_kits WHERE organisation_id = ?", (user.organisation_id,))
    live = sum(1 for k in kits if kit_state(k) == "live")
    recent = store.fetch_all(f"SELECT id, title, status, updated_at FROM reviews WHERE organisation_id = ?{sql} ORDER BY updated_at DESC LIMIT 5", (user.organisation_id, *params))
    return {"counts": {r["status"]: r["n"] for r in rows}, "active_kits": live, "recent": recent}


@router.get("/my-feedback")
def my_feedback(user: User = Depends(require_role("creator"))):
    """What reviewers flagged across the creator's own posts (latest version of each), for charts."""
    posts, by_type, by_sev, fixed, open_ = [], Counter(), Counter(), 0, 0
    for r in store.fetch_all("SELECT id, title, status FROM reviews WHERE organisation_id = ? AND created_by = ? ORDER BY updated_at DESC", (user.organisation_id, user.id)):
        v = latest_version(r["id"])
        fl = findings_for(v["id"], "creator") if v else []
        o = sum(1 for f in fl if f["status"] == "flagged")
        posts.append({"id": r["id"], "title": r["title"], "status": r["status"], "open": o, "fixed": len(fl) - o})
        for f in fl:
            by_type[f["type"]] += 1
            by_sev[f["severity"]] += 1
        open_ += o
        fixed += len(fl) - o
    return {"posts": posts, "by_type": dict(by_type), "by_severity": dict(by_sev), "open": open_, "fixed": fixed}


@router.get("/reviews")
def list_reviews(user: User = Depends(current_user)):
    sql, params = scope(user)
    rows = store.fetch_all(
        f"""SELECT id, title, status, kit_id, created_by, reviewer_id, round, updated_at,
            (SELECT display_name FROM profiles WHERE user_id = reviews.created_by) AS creator_name,
            (SELECT display_name FROM profiles WHERE user_id = reviews.reviewer_id) AS reviewer_name
            FROM reviews WHERE organisation_id = ?{sql} ORDER BY updated_at DESC""", (user.organisation_id, *params))
    return {"reviews": rows}


@router.post("/reviews", status_code=201)
def create_review(body: ReviewCreate, user: User = Depends(require_role("creator"))):
    return _create_review(user, body.kit_id, body.title, body.content, body.content_type)


@router.post("/reviews/upload", status_code=201)
def create_review_from_file(file: UploadFile = File(...), kit_id: str = Form(...), title: str = Form(default=""),
                            content_type: str = Form(default="document"), user: User = Depends(require_role("creator"))):
    """Create a post from a DOCX/PDF (text is extracted; scanned pages use OCR when installed; the file is not kept)."""
    rate_limit(f"upload:{user.id}", 20)
    data = file.file.read(get_settings().max_upload_bytes + 1)
    doc = document_extractor.extract(file.filename or "", data)
    return _create_review(user, kit_id, title.strip() or (file.filename or "Document").rsplit(".", 1)[0], doc["text"][:50000], content_type)


@router.post("/reviews/from-google-doc", status_code=201)
def create_review_from_google_doc(body: GoogleDocReview, user: User = Depends(require_role("creator"))):
    rate_limit(f"upload:{user.id}", 20)
    doc = document_extractor.from_text(gdocs.fetch_text(body.url))
    return _create_review(user, body.kit_id, (body.title or "Google Doc draft").strip(), doc["text"][:50000], body.content_type)


@router.get("/reviews/{rid}")
def get_one(rid: str, version_number: int | None = None, user: User = Depends(current_user)):
    r = get_review(user, rid)
    versions = store.fetch_all(
        """SELECT v.id, v.version_number, v.content, v.created_at, v.analyzed_at, v.analysis_json, v.created_by,
           p.display_name AS author_name, p.role AS author_role FROM review_versions v
           LEFT JOIN profiles p ON p.user_id = v.created_by WHERE v.review_id = ? ORDER BY v.version_number""", (rid,))
    cur = next((v for v in versions if v["version_number"] == version_number), versions[-1])
    kv = store.fetch_one("SELECT version_number FROM brand_kit_versions WHERE id = ?", (r["kit_version_id"],))
    kit = store.fetch_one("SELECT name FROM brand_kits WHERE id = ?", (r["kit_id"],))
    decisions = store.fetch_all("SELECT a.*, p.display_name FROM approval_events a LEFT JOIN profiles p ON p.user_id = a.reviewer_id WHERE a.review_id = ? ORDER BY a.created_at, a.rowid", (rid,))
    comments = store.fetch_all("SELECT c.*, p.display_name FROM review_comments c LEFT JOIN profiles p ON p.user_id = c.author_id WHERE c.review_id = ? ORDER BY c.created_at", (rid,))
    return {"review": {**r, "kit_version_number": kv["version_number"], "kit_name": kit["name"] if kit else "",
                       "creator_name": name_of(r["created_by"]), "reviewer_name": name_of(r["reviewer_id"])},
            "versions": versions, "current_version": cur["version_number"], "latest_version": versions[-1]["version_number"],
            "findings": findings_for(cur["id"], user.role), "images": images_for(cur["id"]), "decisions": decisions, "comments": comments}


@router.post("/reviews/{rid}/findings/{fid}")
def update_finding(rid: str, fid: str, body: FindingUpdate, user: User = Depends(require_role("creator"))):
    own_review(user, rid)
    if body.status in ("open", "dismissed"):
        raise AppError(422, "VALIDATION_ERROR", "Only the reviewer can dismiss a flag. You can accept it, edit the text or mark it as fixed.")
    f = store.fetch_one("SELECT f.* FROM findings f JOIN review_versions v ON v.id = f.review_version_id WHERE f.id = ? AND v.review_id = ?", (fid, rid))
    if not f or f["status"] not in CREATOR_VISIBLE:
        raise AppError(404, "NOT_FOUND", "Finding not found.")
    store.update("findings", fid, status=body.status, final_text=body.final_text)
    touch(rid)
    rule = (f["source_refs"] or [{}])[0].get("title") or f["type"]
    store.audit(user.organisation_id, user.id, f"finding.{body.status}", rid, finding=fid, type=f["type"], rule=rule)
    return {"id": fid, "status": body.status}


def copy_images(old_version_id: str, new_version_id: str):
    for im in images_for(old_version_id):  # attached images (and their alt text) carry forward
        store.insert("review_images", id=store.new_id("img"), review_version_id=new_version_id, filename=im["filename"], alt_text=im["alt_text"],
                     text_color=im["text_color"], bg_color=im["bg_color"], width=im["width"], height=im["height"],
                     dominant_json=im["dominant"], thumb=im["thumb"], created_at=store.now())


@router.post("/reviews/{rid}/revisions", status_code=201)
def revise(rid: str, body: RevisionIn, user: User = Depends(require_role("creator"))):
    _, old = editable_latest(user, rid)
    n = old["version_number"] + 1  # prior versions are never overwritten
    vid = store.new_id("rv")
    store.insert("review_versions", id=vid, review_id=rid, version_number=n, content=body.content, created_by=user.id, created_at=store.now())
    copy_images(old["id"], vid)
    touch(rid, status="draft")
    store.audit(user.organisation_id, user.id, "review.revised", rid, version=n)
    return {"version_number": n}


@router.post("/reviews/{rid}/images", status_code=201)
def add_image(rid: str, file: UploadFile = File(...), alt_text: str = Form(default=""), text_color: str = Form(default=""),
              bg_color: str = Form(default=""), user: User = Depends(require_role("creator"))):
    _, v = editable_latest(user, rid)
    if len(images_for(v["id"])) >= MAX_IMAGES:
        raise AppError(409, "TOO_MANY_IMAGES", f"You can attach up to {MAX_IMAGES} images per version.")
    info = image_checker.analyze_image(file.file.read(image_checker.MAX_IMAGE_BYTES + 1))
    iid = store.new_id("img")
    store.insert("review_images", id=iid, review_version_id=v["id"], filename=re.sub(r"[^\w.\- ]", "_", file.filename or "image")[:120],
                 alt_text=alt_text.strip()[:500], text_color=_color(text_color, "Text colour"), bg_color=_color(bg_color, "Background colour"),
                 width=info["width"], height=info["height"], dominant_json=info["dominant"], thumb=info["thumb"], created_at=store.now())
    touch(rid)
    store.audit(user.organisation_id, user.id, "image.attached", rid, version=v["version_number"])
    return next(i for i in images_for(v["id"]) if i["id"] == iid)


def _image(v: dict, iid: str) -> dict:
    im = next((i for i in images_for(v["id"]) if i["id"] == iid), None)
    if not im:
        raise AppError(404, "NOT_FOUND", "Image not found on the latest version.")
    return im


@router.patch("/reviews/{rid}/images/{iid}")
def update_image(rid: str, iid: str, body: ImageUpdate, user: User = Depends(require_role("creator"))):
    _, v = editable_latest(user, rid)
    _image(v, iid)
    vals = {}
    if body.alt_text is not None:
        vals["alt_text"] = body.alt_text.strip()
    if body.text_color is not None:
        vals["text_color"] = _color(body.text_color, "Text colour")
    if body.bg_color is not None:
        vals["bg_color"] = _color(body.bg_color, "Background colour")
    if vals:
        store.update("review_images", iid, **vals)
    return _image(v, iid)


@router.post("/reviews/{rid}/images/{iid}/suggest-alt")
def suggest_alt(rid: str, iid: str, user: User = Depends(require_role("creator"))):
    """Optional AI help: describe the image for screen readers. Needs LLM_API_KEY; the creator always edits the result."""
    _, v = editable_latest(user, rid)
    im = _image(v, iid)
    if not llm.configured():
        raise AppError(400, "AI_NOT_CONFIGURED", "AI help is switched off. Add LLM_API_KEY on the server to enable alt-text suggestions.")
    rate_limit(f"ai:{user.id}", 20)
    try:
        text = llm.complete_text("You write concise alt text for images used in marketing content. Reply with one sentence under 125 characters, no quotes, no 'image of'.",
                                 "Write alt text for this image.", image_data_uri=im["thumb"])
    except llm.LLMError as e:
        raise AppError(502, "AI_UNAVAILABLE", str(e)) from e
    return {"suggestion": text.strip().strip('"')[:300]}


@router.delete("/reviews/{rid}/images/{iid}")
def delete_image(rid: str, iid: str, user: User = Depends(require_role("creator"))):
    _, v = editable_latest(user, rid)
    store.execute("DELETE FROM review_images WHERE id = ? AND review_version_id = ?", (iid, v["id"]))
    return {"deleted": iid}


@router.post("/reviews/{rid}/request-review")
def request_review(rid: str, body: RequestReviewIn | None = None, user: User = Depends(require_role("creator"))):
    """Creator submits the post to a reviewer (a named one, or any reviewer). The reviewer runs the Brand Kit checks."""
    r = own_review(user, rid)
    if r["status"] not in EDITABLE:
        raise AppError(409, "INVALID_STATE", "This post has already been submitted.")
    v = latest_version(rid)
    last = store.fetch_one("SELECT * FROM approval_events WHERE review_id = ? ORDER BY created_at DESC, rowid DESC", (rid,))
    if last and last["decision"] == "request_changes" and last["version_id"] == v["id"]:
        raise AppError(409, "NO_CHANGES", "The reviewer sent this version back. Make your changes before resubmitting.")
    reviewer_id = (body.reviewer_id if body and body.reviewer_id else None) or r["reviewer_id"]
    if reviewer_id and not store.fetch_one("SELECT 1 AS x FROM profiles WHERE user_id = ? AND organisation_id = ? AND role = 'reviewer'", (reviewer_id, user.organisation_id)):
        raise AppError(422, "VALIDATION_ERROR", "Choose a reviewer from your organisation.")
    touch(rid, status="in_review", reviewer_id=reviewer_id, round=(r["round"] or 0) + 1)
    store.audit(user.organisation_id, user.id, "review.requested", rid, version=v["version_number"], reviewer=reviewer_id, round=(r["round"] or 0) + 1)
    notify.notify(f"BrandSure: \u201c{r['title']}\u201d (version {v['version_number']}) was submitted to {name_of(reviewer_id) or 'the reviewers'}.")
    return {"status": "in_review", "version_number": v["version_number"], "reviewer_id": reviewer_id}


@router.post("/reviews/{rid}/mark-published")
def mark_published(rid: str, user: User = Depends(require_role("creator"))):
    """Record that the approved post went live. BrandSure never publishes anything itself."""
    r = own_review(user, rid)
    if r["status"] != "approved":
        raise AppError(409, "INVALID_STATE", "Only an approved post can be marked as published.")
    touch(rid, status="published")
    store.audit(user.organisation_id, user.id, "review.published", rid, version=latest_version(rid)["version_number"])
    return {"status": "published"}


@router.post("/reviews/{rid}/comments", status_code=201)
def comment(rid: str, body: CommentIn, user: User = Depends(require_role("creator", "reviewer"))):
    get_review(user, rid)
    store.insert("review_comments", id=store.new_id("cmt"), review_id=rid, version_id=latest_version(rid)["id"],
                 author_id=user.id, body=body.body, created_at=store.now())
    return {"ok": True}


@router.get("/reviews/{rid}/audit")
def audit_log(rid: str, user: User = Depends(current_user)):
    get_review(user, rid)
    rows = store.fetch_all("""SELECT a.*, p.display_name FROM audit_events a LEFT JOIN profiles p ON p.user_id = a.actor_id
                              WHERE a.organisation_id = ? AND a.entity_id = ? ORDER BY a.created_at, a.rowid""", (user.organisation_id, rid))
    return {"events": rows}
