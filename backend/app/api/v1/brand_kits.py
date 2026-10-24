from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import User, current_user, rate_limit, require_role
from app.repositories import store
from app.schemas.brand_kit import ConfirmIn, GoogleDocIn
from app.services import candidate_extractor, document_extractor, gdocs, notify
from app.services.text_utils import norm

router = APIRouter(prefix="/brand-kits", tags=["brand-kits"])


def kit_state(k: dict) -> str:
    """needs_confirmation -> ready_to_send -> live (visible to creators) | inactive."""
    if k["status"] == "inactive":
        return "inactive"
    if not k["active_version_id"]:
        return "needs_confirmation"
    return "live" if k["published_at"] else "ready_to_send"


def get_kit(user: User, kit_id: str) -> dict:
    """Organisation-scoped lookup. Creators and reviewers only see kits the admin has sent to creators."""
    kit = store.fetch_one("SELECT * FROM brand_kits WHERE id = ? AND organisation_id = ?", (kit_id, user.organisation_id))
    if not kit or (user.role != "admin" and not kit["published_at"]):
        raise AppError(404, "NOT_FOUND", "Brand Kit not found.")
    return kit


def load_rules(version_id: str) -> list:
    rules = store.fetch_all("SELECT * FROM brand_rules WHERE version_id = ? ORDER BY rowid", (version_id,))
    for r in rules:
        r["params"] = r.pop("params") or {}
        r["source"] = r.pop("source")
    return rules


def _start_extraction(user: User, name: str, filename: str, mime: str, size: int, doc: dict) -> dict:
    cands, warnings, mode = candidate_extractor.extract_candidates(doc["units"])
    if doc.get("ocr_pages"):
        pages = ", ".join(str(p) for p in doc["ocr_pages"])
        warnings.insert(0, f"Pages {pages} were scanned images and were read with OCR. Check the extracted text carefully; OCR can misread words and numbers.")
    kit_id, doc_id = store.new_id("kit"), store.new_id("doc")
    store.insert("brand_kits", id=kit_id, organisation_id=user.organisation_id, name=name, active_version_id=None,
                 created_by=user.id, created_at=store.now())
    store.insert("documents", id=doc_id, organisation_id=user.organisation_id, kit_id=kit_id, filename=filename, mime_type=mime,
                 size_bytes=size, status="needs_confirmation", extracted_text=doc["text"], units_json=doc["units"],
                 candidates_json=cands, warnings_json=warnings, extraction_mode=mode, created_by=user.id, created_at=store.now())
    store.audit(user.organisation_id, user.id, "kit.extracted", kit_id, filename=filename, candidates=len(cands), ocr_pages=len(doc.get("ocr_pages", [])))
    return {"kit_id": kit_id, "document_id": doc_id, "filename": filename, "text": doc["text"], "candidates": cands,
            "warnings": warnings, "extraction_mode": mode}


@router.post("/extract", status_code=201)
def extract(file: UploadFile = File(...), name: str = Form(default=""), user: User = Depends(require_role("admin"))):
    rate_limit(f"extract:{user.id}", 10)
    data = file.file.read(get_settings().max_upload_bytes + 1)
    doc = document_extractor.extract(file.filename or "", data)
    return _start_extraction(user, name.strip() or (file.filename or "Brand Kit").rsplit(".", 1)[0], file.filename or "", file.content_type or "", len(data), doc)


@router.post("/extract-google-doc", status_code=201)
def extract_google_doc(body: GoogleDocIn, user: User = Depends(require_role("admin"))):
    rate_limit(f"extract:{user.id}", 10)
    doc = document_extractor.from_text(gdocs.fetch_text(body.url))
    return _start_extraction(user, (body.name or "").strip() or "Google Doc guidelines", f"Google Doc {gdocs.doc_id(body.url)[:8]}", "text/plain", len(doc["text"]), doc)


@router.get("")
def list_kits(user: User = Depends(current_user)):
    kits = store.fetch_all("SELECT * FROM brand_kits WHERE organisation_id = ? ORDER BY created_at DESC", (user.organisation_id,))
    out = []
    for k in kits:
        k["state"] = kit_state(k)
        if user.role != "admin" and k["state"] != "live":
            continue
        v = store.fetch_one("SELECT version_number FROM brand_kit_versions WHERE id = ?", (k["active_version_id"],)) if k["active_version_id"] else None
        k["active_version_number"] = v["version_number"] if v else None
        k["reviews_count"] = store.fetch_one("SELECT COUNT(*) AS n FROM reviews WHERE kit_id = ?", (k["id"],))["n"]
        out.append(k)
    return {"kits": out}


@router.get("/{kit_id}")
def get_one(kit_id: str, user: User = Depends(current_user)):
    kit = get_kit(user, kit_id)
    kit["state"] = kit_state(kit)
    kit["reviews_count"] = store.fetch_one("SELECT COUNT(*) AS n FROM reviews WHERE kit_id = ?", (kit_id,))["n"]
    version = store.fetch_one("SELECT * FROM brand_kit_versions WHERE id = ?", (kit["active_version_id"],)) if kit["active_version_id"] else None
    doc = store.fetch_one("SELECT * FROM documents WHERE kit_id = ? ORDER BY created_at DESC", (kit_id,))
    pending = bool(doc and doc["status"] == "needs_confirmation")
    out = {"kit": kit, "version": version, "rules": load_rules(version["id"]) if version else [],
           "document": {"filename": doc["filename"], "status": doc["status"]} if doc else None}
    if pending and user.role == "admin":  # reload the confirmation screen after refresh
        out["extraction"] = {"text": doc["extracted_text"], "candidates": doc["candidates"], "warnings": doc["warnings"]}
    return out


@router.post("/{kit_id}/confirm", status_code=201)
def confirm(kit_id: str, body: ConfirmIn, user: User = Depends(require_role("admin"))):
    kit = get_kit(user, kit_id)
    doc = store.fetch_one("SELECT * FROM documents WHERE kit_id = ? ORDER BY created_at DESC", (kit_id,))
    full = norm(doc["extracted_text"]) if doc else ""
    last = store.fetch_one("SELECT MAX(version_number) AS n FROM brand_kit_versions WHERE kit_id = ?", (kit_id,))
    vid, number = store.new_id("ver"), (last["n"] or 0) + 1
    store.insert("brand_kit_versions", id=vid, kit_id=kit_id, version_number=number, status="confirmed",
                 confirmed_by=user.id, confirmed_at=store.now(), created_at=store.now())
    for r in body.rules:
        src = dict(r.source or {})
        if src.get("quote"):
            src["quote_verified"] = norm(src["quote"]) in full  # admin may have edited; flag if no longer verbatim
        store.insert("brand_rules", id=store.new_id("rule"), version_id=vid, type=r.type, title=r.title, content=r.content,
                     severity=r.severity, valid_from=r.valid_from.isoformat() if r.valid_from else None,
                     valid_until=r.valid_until.isoformat() if r.valid_until else None, params_json=r.params or {}, source_json=src or None)
    store.update("brand_kits", kit_id, active_version_id=vid)
    if doc:
        store.update("documents", doc["id"], status="confirmed")
    store.audit(user.organisation_id, user.id, "kit.confirmed", kit_id, version=number, rules=len(body.rules))
    return {"kit_id": kit["id"], "version_id": vid, "version_number": number}


@router.post("/{kit_id}/publish")
def publish(kit_id: str, user: User = Depends(require_role("admin"))):
    """Send the confirmed kit to creators. Until then creators cannot see or use it."""
    kit = get_kit(user, kit_id)
    if not kit["active_version_id"]:
        raise AppError(409, "KIT_NOT_CONFIRMED", "Confirm the rules before sending this kit to creators.")
    if kit["status"] == "inactive":
        raise AppError(409, "KIT_INACTIVE", "Activate this kit before sending it to creators.")
    store.update("brand_kits", kit_id, published_at=store.now(), published_by=user.id)
    store.audit(user.organisation_id, user.id, "kit.published", kit_id)
    notify.notify(f"BrandSure: the Brand Kit \u201c{kit['name']}\u201d is ready. Creators can start checking posts.")
    return {"state": "live"}


@router.post("/{kit_id}/deactivate")
def deactivate(kit_id: str, user: User = Depends(require_role("admin"))):
    """Hide the kit from new posts. Existing reviews keep the kit version they were checked against."""
    get_kit(user, kit_id)
    store.update("brand_kits", kit_id, status="inactive")
    store.audit(user.organisation_id, user.id, "kit.deactivated", kit_id)
    return {"state": "inactive"}


@router.post("/{kit_id}/activate")
def activate(kit_id: str, user: User = Depends(require_role("admin"))):
    kit = get_kit(user, kit_id)
    store.update("brand_kits", kit_id, status="active")
    store.audit(user.organisation_id, user.id, "kit.activated", kit_id)
    return {"state": kit_state({**kit, "status": "active"})}


@router.delete("/{kit_id}")
def delete_kit(kit_id: str, user: User = Depends(require_role("admin"))):
    kit = get_kit(user, kit_id)
    n = store.fetch_one("SELECT COUNT(*) AS n FROM reviews WHERE kit_id = ?", (kit_id,))["n"]
    if n:
        raise AppError(409, "KIT_IN_USE", f"{n} post(s) were checked against this kit, so it cannot be deleted. Deactivate it instead.")
    store.execute("UPDATE brand_kits SET active_version_id = NULL WHERE id = ?", (kit_id,))
    store.execute("DELETE FROM brand_rules WHERE version_id IN (SELECT id FROM brand_kit_versions WHERE kit_id = ?)", (kit_id,))
    store.execute("DELETE FROM brand_kit_versions WHERE kit_id = ?", (kit_id,))
    store.execute("DELETE FROM documents WHERE kit_id = ?", (kit_id,))
    store.execute("DELETE FROM brand_kits WHERE id = ?", (kit_id,))
    store.audit(user.organisation_id, user.id, "kit.deleted", kit_id, name=kit["name"])
    return {"deleted": kit_id}


@router.get("/{kit_id}/versions")
def versions(kit_id: str, user: User = Depends(require_role("admin", "reviewer"))):
    get_kit(user, kit_id)
    return {"versions": store.fetch_all("SELECT * FROM brand_kit_versions WHERE kit_id = ? ORDER BY version_number DESC", (kit_id,))}
