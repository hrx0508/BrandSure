"""Governance insights computed ONLY from recorded events (analysis runs, dismissals, decisions)."""
from datetime import datetime

from app.repositories import store

MIN_SHOWN = 3  # do not call a rule "unclear" from fewer observations


def _ts(s):
    return datetime.fromisoformat(s)


def build_insights(org_id: str) -> dict:
    events = store.fetch_all("SELECT * FROM audit_events WHERE organisation_id = ? ORDER BY created_at, rowid", (org_id,))
    latest_run = {}  # newest analysis per (review, version): repeated runs are not double counted
    dismissed, accepted, flagged, requested, turnaround = {}, {}, {}, {}, []
    for e in events:
        m, act = e["metadata"] or {}, e["action"]
        if act == "review.analyzed":
            latest_run[(e["entity_id"], m.get("version"))] = m
        elif act == "finding.dismissed":
            dismissed[m.get("rule")] = dismissed.get(m.get("rule"), 0) + 1
        elif act == "finding.flagged":
            flagged[m.get("rule")] = flagged.get(m.get("rule"), 0) + 1
        elif act in ("finding.accepted", "finding.edited"):
            accepted[m.get("rule")] = accepted.get(m.get("rule"), 0) + 1
        elif act == "review.requested":
            requested[e["entity_id"]] = e["created_at"]
        elif act in ("review.approved", "review.changes_requested") and e["entity_id"] in requested:
            turnaround.append((_ts(e["created_at"]) - _ts(requested.pop(e["entity_id"]))).total_seconds() / 3600)
    by_type, shown = {}, {}
    for m in latest_run.values():
        for k, v in (m.get("by_type") or {}).items():
            by_type[k] = by_type.get(k, 0) + v
        for k, v in (m.get("by_rule") or {}).items():
            shown[k] = shown.get(k, 0) + v
    rules = []
    for title, n in shown.items():
        d, a, fl = dismissed.get(title, 0), accepted.get(title, 0), flagged.get(title, 0)
        rate = min(d / n, 1.0) if n >= MIN_SHOWN else None
        rules.append({"title": title, "shown": n, "dismissed": d, "accepted": a, "flagged": fl,
                      "dismiss_rate": round(rate, 2) if rate is not None else None,
                      "possibly_unclear": bool(rate is not None and rate >= 0.5)})
    rules.sort(key=lambda r: (-(r["dismiss_rate"] or 0), -r["shown"]))
    timeline = {}
    for e in events:
        if e["action"] == "review.analyzed" and latest_run.get((e["entity_id"], (e["metadata"] or {}).get("version"))) is e["metadata"]:
            d = e["created_at"][:10]
            row = timeline.setdefault(d, {"date": d, "versions": 0, "findings": 0})
            row["versions"] += 1
            row["findings"] += (e["metadata"] or {}).get("findings", 0)
    decisions = {r["decision"]: r["n"] for r in store.fetch_all(
        "SELECT a.decision, COUNT(*) AS n FROM approval_events a JOIN reviews r ON r.id = a.review_id WHERE r.organisation_id = ? GROUP BY a.decision", (org_id,))}
    rounds = store.fetch_one("SELECT AVG(round) AS a FROM reviews WHERE organisation_id = ? AND status IN ('approved','published') AND round > 0", (org_id,))["a"]
    counts = {r["status"]: r["n"] for r in store.fetch_all("SELECT status, COUNT(*) AS n FROM reviews WHERE organisation_id = ? GROUP BY status", (org_id,))}
    decided = counts.get("approved", 0) + counts.get("changes_requested", 0)
    return {"insufficient_data": not latest_run, "timeline": sorted(timeline.values(), key=lambda x: x["date"]), "decisions": decisions,
            "avg_rounds": round(rounds, 1) if rounds else None, "versions_analyzed": len(latest_run),
            "by_type": sorted(({"type": k, "count": v} for k, v in by_type.items()), key=lambda x: -x["count"]),
            "rules": rules,
            "reviews": {"counts": counts, "avg_hours_to_decision": round(sum(turnaround) / len(turnaround), 2) if turnaround else None,
                        "changes_requested_rate": round(counts.get("changes_requested", 0) / decided, 2) if decided else None}}
