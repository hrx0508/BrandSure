"""Role-specific work lists: what this person has to do now, and what they are waiting for from others."""
from app.api.v1.brand_kits import kit_state
from app.repositories import store


def _latest(review_id):
    return store.fetch_one("SELECT * FROM review_versions WHERE review_id = ? ORDER BY version_number DESC", (review_id,))


def _flagged(review_id) -> int:
    v = _latest(review_id)
    return store.fetch_one("SELECT COUNT(*) AS n FROM findings WHERE review_version_id = ? AND status = 'flagged'", (v["id"],))["n"] if v else 0


def _t(kind, title, detail, link, at=None):
    return {"kind": kind, "title": title, "detail": detail, "link": link, "at": at}


def build_tasks(user) -> dict:
    org, todo, waiting = user.organisation_id, [], []
    names = {p["user_id"]: p["display_name"] for p in store.fetch_all("SELECT user_id, display_name FROM profiles WHERE organisation_id = ?", (org,))}
    reviews = store.fetch_all("SELECT * FROM reviews WHERE organisation_id = ? ORDER BY updated_at DESC", (org,))

    if user.role == "admin":
        kits = store.fetch_all("SELECT * FROM brand_kits WHERE organisation_id = ?", (org,))
        used = {r["kit_id"] for r in reviews}
        for k in kits:
            s = kit_state(k)
            link = f"/brand-kits/{k['id']}"
            if s == "needs_confirmation":
                todo.append(_t("kit_confirm", f"Confirm the rules for \u201c{k['name']}\u201d", "Check the proposed rules against the source text, then confirm.", link, k["created_at"]))
            elif s == "ready_to_send":
                todo.append(_t("kit_send", f"Send \u201c{k['name']}\u201d to creators", "The kit is confirmed but creators cannot use it yet.", link, k["created_at"]))
            elif s == "live" and k["id"] not in used:
                waiting.append(_t("kit_wait", f"Waiting for creators to use \u201c{k['name']}\u201d", "No post has been checked against this kit yet.", link, k["published_at"]))
        if not kits:
            todo.append(_t("kit_new", "Upload your brand guidelines", "Create the first Brand Kit from a PDF, DOCX or Google Doc.", "/brand-kits"))
        n_rev = sum(1 for r in reviews if r["status"] == "in_review")
        n_cre = sum(1 for r in reviews if r["status"] in ("draft", "changes_requested"))
        if n_rev:
            waiting.append(_t("with_reviewers", f"{n_rev} post(s) waiting for reviewers", "Reviewers decide on these.", "/posts"))
        if n_cre:
            waiting.append(_t("with_creators", f"{n_cre} post(s) being prepared by creators", "Drafts and requested changes.", "/posts"))

    elif user.role == "creator":
        for r in reviews:
            if r["created_by"] != user.id:
                continue
            link, who = f"/posts/{r['id']}", names.get(r["reviewer_id"]) or "a reviewer"
            if r["status"] == "changes_requested":
                n = _flagged(r["id"])
                todo.append(_t("fix", f"Fix what {who} flagged in “{r['title']}”", f"{n} flagged item(s) to fix. Then resubmit." if n else "Read the reviewer's note, make changes and resubmit.", link, r["updated_at"]))
            elif r["status"] == "draft":
                todo.append(_t("submit", f"Finish and submit “{r['title']}”", "Write your post, attach images, then submit it to a reviewer.", link, r["updated_at"]))
            elif r["status"] == "approved":
                todo.append(_t("publish", f"Publish “{r['title']}”", "It was approved. Post it, then mark it as published.", link, r["updated_at"]))
            elif r["status"] == "in_review":
                waiting.append(_t("wait_reviewer", f"Waiting for {who} to review “{r['title']}”", f"Round {r['round']}.", link, r["updated_at"]))

    else:  # reviewer
        for r in reviews:
            link = f"/posts/{r['id']}"
            mine = r["reviewer_id"] in (None, user.id)
            if r["status"] == "in_review" and mine and r["created_by"] != user.id:
                started = bool((_latest(r["id"]) or {}).get("analyzed_at"))
                who = names.get(r["created_by"])
                if started:
                    todo.append(_t("decide", f"Finish reviewing “{r['title']}”", f"From {who}. Flag or dismiss the findings, then decide.", link, r["updated_at"]))
                else:
                    todo.append(_t("start_review", f"Start review: “{r['title']}”", f"From {who}. Round {r['round']}." + ("" if r["reviewer_id"] else " Open to any reviewer."), link, r["updated_at"]))
            elif r["status"] == "changes_requested" and r["reviewer_id"] == user.id:
                waiting.append(_t("wait_creator", f"Waiting for {names.get(r['created_by'])} to fix “{r['title']}”", "You sent it back.", link, r["updated_at"]))
    return {"todo": todo, "waiting": waiting}
