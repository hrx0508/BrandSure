"""End-to-end API tests (need fastapi, httpx, python-multipart)."""
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("multipart")
from fastapi.testclient import TestClient  # noqa: E402

from tests.helpers import SAMPLE_DRAFT, make_docx  # noqa: E402

API = "/api/v1"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _client(tmp_path, monkeypatch, demo_content):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("EVAL_DATE", "2026-10-20")
    monkeypatch.setenv("DEMO_CONTENT", demo_content)
    monkeypatch.setenv("DEMO_LOGIN", "true")
    from app.core import security
    security._hits.clear()
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def client(tmp_path, monkeypatch):  # empty organisation
    with _client(tmp_path, monkeypatch, "false") as c:
        yield c


@pytest.fixture()
def demo_client(tmp_path, monkeypatch):  # organisation with the sample content
    with _client(tmp_path, monkeypatch, "true") as c:
        yield c


def auth(client, who):
    r = client.post(f"{API}/auth/login", json={"email": f"{who}@brandsure.demo", "password": "brandsure123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def login(client, email, pw="longenough1"):
    r = client.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def demo(client, role):
    r = client.post(f"{API}/demo/login", json={"role": role})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == role
    return {"Authorization": "Bearer " + r.json()["token"]}


def png(color=(230, 30, 30)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (60, 60), color).save(b, "PNG")
    return b.getvalue()


def make_kit(client, A):
    r = client.post(f"{API}/brand-kits/extract", headers=A, files={"file": ("g.docx", make_docx(), DOCX)})
    assert r.status_code == 201, r.text
    body = r.json()
    rules = [{k: c[k] for k in ("type", "title", "content", "severity", "valid_until", "params", "source")} for c in body["candidates"]]
    rules.append({"type": "fact", "title": "Fact", "content": "TechNova was ranked No. 1 productivity platform in Asia.", "severity": "low", "params": {}})
    r = client.post(f"{API}/brand-kits/{body['kit_id']}/confirm", headers=A, json={"rules": rules})
    assert r.status_code == 201, r.text
    assert client.post(f"{API}/brand-kits/{body['kit_id']}/publish", headers=A).status_code == 200  # admin sends it to creators
    return body["kit_id"]


def new_post(client, C, kit, title="Post", content="Tech Nova is a fine platform for everyone."):
    r = client.post(f"{API}/reviews", headers=C, json={"kit_id": kit, "title": title, "content": content})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def start(client, R, rid, rerun=False):
    r = client.post(f"{API}/reviews/{rid}/start-review", headers=R, json={"rerun": rerun})
    assert r.status_code == 200, r.text
    return r.json()


def creator_findings(client, C, rid):
    return client.get(f"{API}/reviews/{rid}", headers=C).json()["findings"]


# ------------------------------------------------------------------ auth & isolation
def test_authentication(client):
    assert client.get(f"{API}/brand-kits").status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "admin@brandsure.demo", "password": "nope"}).status_code == 401
    assert client.get(f"{API}/brand-kits", headers={"Authorization": "Bearer abc.def"}).status_code == 401
    r = client.post(f"{API}/auth/register", json={"organisation_name": "Acme", "display_name": "Zed", "email": "zed@acme.test", "password": "longenough1"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "admin"
    assert client.post(f"{API}/auth/register", json={"organisation_name": "Acme", "display_name": "Zed", "email": "ZED@acme.test", "password": "longenough1"}).status_code == 409
    other = {"Authorization": "Bearer " + r.json()["token"]}
    kit = make_kit(client, auth(client, "admin"))
    assert client.get(f"{API}/brand-kits/{kit}", headers=other).status_code == 404  # other organisation cannot see it


# ------------------------------------------------------------------ roles stay separate
def test_creator_writes_reviewer_reviews_creator_sees_only_flags(client):
    A, C, R = auth(client, "admin"), auth(client, "creator"), auth(client, "reviewer")
    kit = make_kit(client, A)
    rid = new_post(client, C, kit, content=SAMPLE_DRAFT)
    img = client.post(f"{API}/reviews/{rid}/images", headers=C, files={"file": ("hero.png", png(), "image/png")},
                      data={"alt_text": "", "text_color": "#FFFFFF", "bg_color": "#F4B6C2"})
    assert img.status_code == 201, img.text
    # creators have no way to run checks; reviewers cannot see drafts; creators cannot use reviewer actions
    assert client.post(f"{API}/reviews/{rid}/analyze", headers=C, json={}).status_code in (404, 405)
    assert client.post(f"{API}/reviews/{rid}/start-review", headers=C, json={}).status_code == 403
    assert client.get(f"{API}/reviews/{rid}", headers=R).status_code == 404
    assert client.post(f"{API}/reviews/{rid}/request-review", headers=C, json={}).status_code == 200  # submit, no checks needed
    assert creator_findings(client, C, rid) == []
    # reviewer starts the review: Brand Kit + image checks run, but the creator still sees nothing
    res = start(client, R, rid)
    types = {f["type"] for f in res["findings"]}
    assert {"terminology", "expired_offer", "date_conflict", "unsupported_claim", "missing_alt", "low_contrast", "visual_palette"} <= types
    assert all(f["status"] == "open" for f in res["findings"])
    assert creator_findings(client, C, rid) == []
    assert client.post(f"{API}/reviews/{rid}/start-review", headers=R, json={}).status_code == 409  # already started
    # approving needs high-severity findings to be acknowledged
    d = {"decision": "approve", "version_number": 1}
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json=d).status_code == 422
    # the reviewer decides what is a real problem
    by = {f["type"]: f for f in res["findings"]}
    assert client.post(f"{API}/reviews/{rid}/findings/{by['terminology']['id']}/triage", headers=R, json={"action": "flag"}).status_code == 200
    assert client.post(f"{API}/reviews/{rid}/findings/{by['unsupported_claim']['id']}/triage", headers=R, json={"action": "dismiss"}).status_code == 200
    seen = creator_findings(client, C, rid)
    assert [f["type"] for f in seen] == ["terminology"] and seen[0]["status"] == "flagged"
    assert client.post(f"{API}/reviews/{rid}/findings/{by['terminology']['id']}/triage", headers=C, json={"action": "dismiss"}).status_code == 403
    assert client.post(f"{API}/reviews/{rid}/findings/{by['terminology']['id']}", headers=C, json={"status": "dismissed"}).status_code == 422
    assert client.post(f"{API}/reviews/{rid}/findings/{by['expired_offer']['id']}", headers=C, json={"status": "resolved"}).status_code == 404  # not flagged: invisible
    assert client.post(f"{API}/reviews/{rid}/decision", headers=C, json={**d, "reason": "ok"}).status_code == 403
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json={**d, "reason": "accepting the open risks"}).status_code == 200
    assert client.post(f"{API}/reviews/{rid}/revisions", headers=C, json={"content": "x"}).status_code == 409  # locked after approval
    assert client.post(f"{API}/reviews/{rid}/mark-published", headers=C).status_code == 200
    audit = client.get(f"{API}/reviews/{rid}/audit", headers=R).json()["events"]
    assert audit[-1]["action"] == "review.published"
    ins = client.get(f"{API}/insights", headers=R).json()
    assert ins["insufficient_data"] is False and ins["versions_analyzed"] == 1
    rule = next(x for x in ins["rules"] if x["flagged"])
    assert rule["flagged"] == 1


def test_full_loop_suggestions_edit_resubmit_approve(client):
    A, C, R = auth(client, "admin"), auth(client, "creator"), auth(client, "reviewer")
    kit = make_kit(client, A)
    client.post(f"{API}/users", headers=A, json={"display_name": "Other Rev", "email": "o@x.test", "password": "longenough1", "role": "reviewer"})
    R2 = login(client, "o@x.test")
    reviewer_id = next(x["id"] for x in client.get(f"{API}/reviewers", headers=C).json()["reviewers"] if x["display_name"].startswith("Riya"))
    text = "Tech Nova is a fine platform for everyone."
    rid = new_post(client, C, kit, content=text)
    assert client.post(f"{API}/reviews/{rid}/request-review", headers=C, json={"reviewer_id": "nobody"}).status_code == 422
    assert client.post(f"{API}/reviews/{rid}/request-review", headers=C, json={"reviewer_id": reviewer_id}).status_code == 200
    assert [t["kind"] for t in client.get(f"{API}/tasks", headers=R).json()["todo"]] == ["start_review"]
    assert client.get(f"{API}/tasks", headers=R2).json()["todo"] == []  # it was sent to Riya
    assert [t["kind"] for t in client.get(f"{API}/tasks", headers=C).json()["waiting"]] == ["wait_reviewer"]
    assert client.post(f"{API}/reviews/{rid}/start-review", headers=R2, json={}).status_code == 403
    start(client, R, rid)
    assert [t["kind"] for t in client.get(f"{API}/tasks", headers=R).json()["todo"]] == ["decide"]
    # suggestion on a selected range (checked against the exact version), then flag everything open
    i = text.index("fine platform")
    assert client.post(f"{API}/reviews/{rid}/suggestions", headers=R, json={"version_number": 1, "start": 0, "end": 9999, "replacement": "x", "note": "n"}).status_code == 422
    s = client.post(f"{API}/reviews/{rid}/suggestions", headers=R, json={"version_number": 1, "start": i, "end": i + 13, "replacement": "great platform", "note": "Be specific"})
    assert s.status_code == 201 and s.json()["origin"] == "reviewer" and s.json()["status"] == "flagged"
    assert client.post(f"{API}/reviews/{rid}/triage-all", headers=R).json()["flagged"] >= 1
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json={"decision": "request_changes", "version_number": 1}).status_code == 422
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json={"decision": "request_changes", "version_number": 1, "reason": "see the flags"}).status_code == 200
    # the creator now has flagged work, and must change something before resubmitting
    assert [t["kind"] for t in client.get(f"{API}/tasks", headers=C).json()["todo"]] == ["fix"]
    assert [t["kind"] for t in client.get(f"{API}/tasks", headers=R).json()["waiting"]] == ["wait_creator"]
    flags = creator_findings(client, C, rid)
    assert {f["type"] for f in flags} >= {"terminology", "reviewer_suggestion"}
    assert client.post(f"{API}/reviews/{rid}/request-review", headers=C, json={}).status_code == 409
    sug = next(f for f in flags if f["origin"] == "reviewer")
    assert client.post(f"{API}/reviews/{rid}/findings/{sug['id']}", headers=C, json={"status": "accepted"}).status_code == 200
    assert client.post(f"{API}/reviews/{rid}/revisions", headers=C, json={"content": "TechNova is a great platform for everyone."}).status_code == 201
    assert creator_findings(client, C, rid) == []  # the new version has not been reviewed yet
    assert client.post(f"{API}/reviews/{rid}/request-review", headers=C, json={}).status_code == 200  # resubmit to the same reviewer
    assert client.get(f"{API}/reviews/{rid}", headers=C).json()["review"]["round"] == 2
    start(client, R, rid)
    # reviewer edits the post directly: a new version by the reviewer, back to the creator
    e = client.post(f"{API}/reviews/{rid}/reviewer-edit", headers=R, json={"version_number": 2, "content": "TechNova is a great platform.", "note": "Tighter"})
    assert e.status_code == 201 and e.json()["status"] == "changes_requested"
    body = client.get(f"{API}/reviews/{rid}", headers=C).json()
    assert body["versions"][-1]["author_role"] == "reviewer" and body["review"]["status"] == "changes_requested"
    assert client.post(f"{API}/reviews/{rid}/request-review", headers=C, json={}).status_code == 200  # creator confirms the edited version
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json={"decision": "approve", "version_number": 3}).status_code == 409  # review of v3 not started
    start(client, R, rid)
    assert client.post(f"{API}/reviews/{rid}/mark-published", headers=C).status_code == 409
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json={"decision": "approve", "version_number": 2}).status_code == 409  # stale
    r = client.post(f"{API}/reviews/{rid}/decision", headers=R, json={"decision": "approve", "version_number": 3, "reason": "good"})
    assert r.status_code == 200, r.text
    assert [t["kind"] for t in client.get(f"{API}/tasks", headers=C).json()["todo"]] == ["publish"]
    assert client.post(f"{API}/reviews/{rid}/mark-published", headers=C).status_code == 200
    ins = client.get(f"{API}/insights", headers=A).json()
    assert ins["decisions"].get("approve") == 1 and ins["decisions"].get("request_changes") == 1 and ins["avg_rounds"] == 3.0


def test_reject_admin_tasks_integrations(client):
    A, C, R = auth(client, "admin"), auth(client, "creator"), auth(client, "reviewer")
    assert [x["kind"] for x in client.get(f"{API}/tasks", headers=A).json()["todo"]] == ["kit_new"]
    kit = make_kit(client, A)
    assert [x["kind"] for x in client.get(f"{API}/tasks", headers=A).json()["waiting"]] == ["kit_wait"]
    rid = new_post(client, C, kit, "Bad post", "A cheap deal")
    client.post(f"{API}/reviews/{rid}/request-review", headers=C, json={})
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json={"decision": "reject", "version_number": 1}).status_code == 422
    assert client.post(f"{API}/reviews/{rid}/decision", headers=R, json={"decision": "reject", "version_number": 1, "reason": "Off brief"}).status_code == 200
    assert client.get(f"{API}/reviews/{rid}", headers=C).json()["review"]["status"] == "rejected"
    assert client.post(f"{API}/reviews/{rid}/revisions", headers=C, json={"content": "x"}).status_code == 409
    assert client.get(f"{API}/integrations", headers=C).status_code == 403
    ints = {i["id"]: i for i in client.get(f"{API}/integrations", headers=A).json()["integrations"]}
    assert ints["slack"]["configured"] is False and ints["ai"]["configured"] is False and ints["google_docs"]["configured"] is True
    h = client.get(f"{API}/health").json()
    assert h["ai_enabled"] is False and h["auth_provider"] == "local"


# ------------------------------------------------------------------ kits
def test_kit_lifecycle_publish_deactivate_delete(client):
    A, C = auth(client, "admin"), auth(client, "creator")
    body = client.post(f"{API}/brand-kits/extract", headers=A, files={"file": ("g.docx", make_docx(), DOCX)}).json()
    kit = body["kit_id"]
    rules = [{k: c[k] for k in ("type", "title", "content", "severity", "valid_until", "params", "source")} for c in body["candidates"]]
    assert client.post(f"{API}/brand-kits/{kit}/publish", headers=A).status_code == 409  # not confirmed yet
    client.post(f"{API}/brand-kits/{kit}/confirm", headers=A, json={"rules": rules})
    assert client.get(f"{API}/brand-kits", headers=C).json()["kits"] == []  # confirmed but not sent
    assert client.get(f"{API}/brand-kits/{kit}", headers=C).status_code == 404
    assert client.post(f"{API}/reviews", headers=C, json={"kit_id": kit, "title": "t", "content": "x"}).status_code == 404
    assert client.post(f"{API}/brand-kits/{kit}/publish", headers=C).status_code == 403
    assert client.get(f"{API}/brand-kits", headers=A).json()["kits"][0]["state"] == "ready_to_send"
    assert client.post(f"{API}/brand-kits/{kit}/publish", headers=A).status_code == 200
    assert client.get(f"{API}/brand-kits", headers=C).json()["kits"][0]["state"] == "live"
    rid = new_post(client, C, kit, "t", "x")
    assert client.post(f"{API}/brand-kits/{kit}/deactivate", headers=C).status_code == 403
    assert client.post(f"{API}/brand-kits/{kit}/deactivate", headers=A).status_code == 200
    assert client.get(f"{API}/brand-kits", headers=C).json()["kits"] == []
    assert client.post(f"{API}/reviews", headers=C, json={"kit_id": kit, "title": "t2", "content": "x"}).status_code == 409
    assert client.get(f"{API}/reviews/{rid}", headers=C).status_code == 200
    r = client.delete(f"{API}/brand-kits/{kit}", headers=A)
    assert r.status_code == 409 and r.json()["error"]["code"] == "KIT_IN_USE"
    assert client.post(f"{API}/brand-kits/{kit}/activate", headers=A).status_code == 200
    other = make_kit(client, A)
    assert client.delete(f"{API}/brand-kits/{other}", headers=C).status_code == 403
    assert client.delete(f"{API}/brand-kits/{other}", headers=A).status_code == 200


# ------------------------------------------------------------------ misc
def test_revision_preserves_original_and_carries_images(client):
    A, C = auth(client, "admin"), auth(client, "creator")
    rid = new_post(client, C, make_kit(client, A), "t", "Tech Nova")
    client.post(f"{API}/reviews/{rid}/images", headers=C, files={"file": ("a.png", png(), "image/png")}, data={"alt_text": "A"})
    client.post(f"{API}/reviews/{rid}/revisions", headers=C, json={"content": "TechNova"})
    body = client.get(f"{API}/reviews/{rid}", headers=C).json()
    assert [v["content"] for v in body["versions"]] == ["Tech Nova", "TechNova"]
    assert body["current_version"] == 2 and body["images"][0]["alt_text"] == "A"


def test_post_from_uploaded_document(client):
    A, C = auth(client, "admin"), auth(client, "creator")
    kit = make_kit(client, A)
    r = client.post(f"{API}/reviews/upload", headers=C, files={"file": ("draft.docx", make_docx(["Tech Nova is a great productivity platform and we mean it, really, truly."]), DOCX)},
                    data={"kit_id": kit, "title": "From file"})
    assert r.status_code == 201, r.text
    assert "Tech Nova" in client.get(f"{API}/reviews/{r.json()['id']}", headers=C).json()["versions"][0]["content"]


def test_bad_uploads(client):
    A, C = auth(client, "admin"), auth(client, "creator")
    r = client.post(f"{API}/brand-kits/extract", headers=A, files={"file": ("a.txt", b"hi", "text/plain")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    rid = new_post(client, C, make_kit(client, A), "t", "x")
    r = client.post(f"{API}/reviews/{rid}/images", headers=C, files={"file": ("a.png", b"not an image", "image/png")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "UNSUPPORTED_IMAGE"
    assert client.patch(f"{API}/reviews/{rid}/images/none", headers=C, json={"bg_color": "red"}).status_code in (404, 422)


# ------------------------------------------------------------------ one-click demo
def test_one_click_demo_gives_each_role_its_own_work(demo_client):
    c = demo_client
    assert c.get(f"{API}/health").json()["demo_login"] is True
    A, C, R = demo(c, "admin"), demo(c, "creator"), demo(c, "reviewer")
    assert [k["state"] for k in c.get(f"{API}/brand-kits", headers=C).json()["kits"]] == ["live"]
    assert sorted(t["kind"] for t in c.get(f"{API}/tasks", headers=C).json()["todo"]) == ["fix", "submit"]
    assert [t["kind"] for t in c.get(f"{API}/tasks", headers=R).json()["todo"]] == ["start_review"]
    assert sorted(t["kind"] for t in c.get(f"{API}/tasks", headers=A).json()["waiting"]) == ["with_creators", "with_reviewers"]
    assert c.get(f"{API}/insights", headers=A).json()["insufficient_data"] is False
    posts = {p["title"]: p for p in c.get(f"{API}/reviews", headers=C).json()["reviews"]}
    sent_back = c.get(f"{API}/reviews/{posts['Team planner post']['id']}", headers=C).json()
    assert sent_back["review"]["status"] == "changes_requested" and len(sent_back["findings"]) >= 3
    assert all(f["status"] == "flagged" for f in sent_back["findings"])  # the creator sees only what the reviewer flagged
    fb = c.get(f"{API}/my-feedback", headers=C).json()
    assert fb["open"] >= 3 and "reviewer_suggestion" in fb["by_type"] and any(p["open"] for p in fb["posts"])
    assert c.get(f"{API}/my-feedback", headers=R).status_code == 403
    # the reviewer starts the submitted post
    queue = {p["title"]: p for p in c.get(f"{API}/reviews", headers=R).json()["reviews"]}
    assert "Launch post (draft)" not in queue  # drafts are private to the creator
    res = start(c, R, queue["Weekly tips post"]["id"])
    assert {"terminology", "banned_term"} <= {f["type"] for f in res["findings"]}
    # reset restores the sample content
    kit = c.get(f"{API}/brand-kits", headers=C).json()["kits"][0]["id"]
    new_post(c, C, kit, "extra", "x")
    assert len(c.get(f"{API}/reviews", headers=C).json()["reviews"]) == 4
    assert c.post(f"{API}/demo/reset", headers=C).status_code == 200
    assert sorted(r["status"] for r in c.get(f"{API}/reviews", headers=C).json()["reviews"]) == ["changes_requested", "draft", "in_review"]
    assert c.post(f"{API}/demo/reset").status_code == 401


def test_demo_login_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("DEMO_LOGIN", "false")
    assert client.post(f"{API}/demo/login", json={"role": "admin"}).status_code == 404
    assert client.get(f"{API}/health").json()["demo_login"] is False
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DEMO_LOGIN")
    from app.core.config import get_settings
    assert get_settings().demo_login is False  # off by default in production
