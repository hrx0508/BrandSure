"""Tiny data-access layer. Columns ending in _json are (de)serialised automatically."""
import json

from app.db.client import connect, new_id, now  # noqa: F401  (re-exported)


def _load(row):
    if row is None:
        return None
    out = {}
    for k in row.keys():
        v = row[k]
        if k.endswith("_json"):
            out[k[:-5]] = json.loads(v) if v else None
        else:
            out[k] = v
    return out


def _dump(vals: dict) -> dict:
    return {k: (json.dumps(v) if k.endswith("_json") and v is not None else v) for k, v in vals.items()}


def fetch_one(sql, params=()):
    with connect() as c:
        return _load(c.execute(sql, params).fetchone())


def fetch_all(sql, params=()):
    with connect() as c:
        return [_load(r) for r in c.execute(sql, params).fetchall()]


def insert(table: str, **vals) -> None:
    vals = _dump(vals)
    cols = ", ".join(vals)
    marks = ", ".join("?" for _ in vals)
    with connect() as c:
        c.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(vals.values()))


def update(table: str, id_value: str, **vals) -> None:
    vals = _dump(vals)
    sets = ", ".join(f"{k} = ?" for k in vals)
    with connect() as c:
        c.execute(f"UPDATE {table} SET {sets} WHERE id = ?", (*vals.values(), id_value))


def execute(sql, params=()):
    with connect() as c:
        c.execute(sql, params)


def audit(org_id: str, actor_id: str, action: str, entity_id: str, **metadata) -> None:
    insert("audit_events", id=new_id("aud"), organisation_id=org_id, actor_id=actor_id, action=action,
           entity_id=entity_id, metadata_json=metadata or None, created_at=now())
