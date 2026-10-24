import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from app.core.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS organisations (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, organisation_id TEXT NOT NULL REFERENCES organisations(id),
  role TEXT NOT NULL CHECK (role IN ('admin','creator','reviewer')), display_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS brand_kits (id TEXT PRIMARY KEY, organisation_id TEXT NOT NULL, name TEXT NOT NULL,
  active_version_id TEXT, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active', published_at TEXT, published_by TEXT);
CREATE TABLE IF NOT EXISTS brand_kit_versions (id TEXT PRIMARY KEY, kit_id TEXT NOT NULL REFERENCES brand_kits(id),
  version_number INTEGER NOT NULL, status TEXT NOT NULL, confirmed_by TEXT, confirmed_at TEXT, created_at TEXT NOT NULL,
  UNIQUE (kit_id, version_number));
CREATE TABLE IF NOT EXISTS brand_rules (id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES brand_kit_versions(id),
  type TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, severity TEXT NOT NULL,
  valid_from TEXT, valid_until TEXT, params_json TEXT, source_json TEXT);
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, organisation_id TEXT NOT NULL, kit_id TEXT NOT NULL,
  filename TEXT NOT NULL, mime_type TEXT, size_bytes INTEGER, status TEXT NOT NULL, extracted_text TEXT,
  units_json TEXT, candidates_json TEXT, warnings_json TEXT, extraction_mode TEXT, created_by TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, organisation_id TEXT NOT NULL, kit_id TEXT NOT NULL,
  kit_version_id TEXT NOT NULL, title TEXT NOT NULL, content_type TEXT, status TEXT NOT NULL,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  reviewer_id TEXT, round INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS review_versions (id TEXT PRIMARY KEY, review_id TEXT NOT NULL REFERENCES reviews(id),
  version_number INTEGER NOT NULL, content TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
  analyzed_at TEXT, analysis_json TEXT, UNIQUE (review_id, version_number));
CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, review_version_id TEXT NOT NULL REFERENCES review_versions(id),
  type TEXT NOT NULL, severity TEXT NOT NULL, verdict TEXT, span_json TEXT, quoted_text TEXT, explanation TEXT,
  source_ids_json TEXT, source_refs_json TEXT, evidence_status TEXT, suggested_fix TEXT, replacement TEXT,
  status TEXT NOT NULL DEFAULT 'open', final_text TEXT, origin TEXT, requires_human_review INTEGER DEFAULT 1,
  uncertainty TEXT, position INTEGER DEFAULT 0, meta_json TEXT);
CREATE TABLE IF NOT EXISTS review_images (id TEXT PRIMARY KEY, review_version_id TEXT NOT NULL REFERENCES review_versions(id),
  filename TEXT NOT NULL, alt_text TEXT, text_color TEXT, bg_color TEXT, width INTEGER, height INTEGER,
  dominant_json TEXT, thumb TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_comments (id TEXT PRIMARY KEY, review_id TEXT NOT NULL, version_id TEXT,
  author_id TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approval_events (id TEXT PRIMARY KEY, review_id TEXT NOT NULL, version_id TEXT NOT NULL,
  reviewer_id TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, organisation_id TEXT NOT NULL, actor_id TEXT NOT NULL,
  action TEXT NOT NULL, entity_id TEXT, metadata_json TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_reviews_org ON reviews (organisation_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events (organisation_id, entity_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")  # UTC; UI localises


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@contextmanager
def connect():
    c = sqlite3.connect(get_settings().db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


DEMO_PASSWORD = "brandsure123"
DEMO_USERS = [("u_admin", "admin", "Asha (Brand Admin)", "admin@brandsure.demo"),
              ("u_creator", "creator", "Chirag (Creator)", "creator@brandsure.demo"),
              ("u_reviewer", "reviewer", "Riya (Reviewer)", "reviewer@brandsure.demo")]


NEW_COLUMNS = {  # lets databases created by an earlier version upgrade in place
    "brand_kits": [("status", "TEXT NOT NULL DEFAULT 'active'"), ("published_at", "TEXT"), ("published_by", "TEXT")],
    "reviews": [("reviewer_id", "TEXT"), ("round", "INTEGER NOT NULL DEFAULT 0")],
    "findings": [("meta_json", "TEXT")],
}


def _upgrade(c) -> None:
    for table, cols in NEW_COLUMNS.items():
        have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
        for name, decl in cols:
            if name not in have:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def init_db() -> None:
    from app.core.passwords import hash_password
    with connect() as c:
        c.executescript(SCHEMA)
        _upgrade(c)
        if get_settings().seed_demo and not c.execute("SELECT 1 FROM organisations LIMIT 1").fetchone():
            c.execute("INSERT INTO organisations VALUES ('org_demo','Demo Organisation',?)", (now(),))
            pw = hash_password(DEMO_PASSWORD)
            c.executemany("INSERT INTO profiles VALUES (?,?,?,?,?,?)",
                          [(u, "org_demo", role, name, email, pw) for u, role, name, email in DEMO_USERS])
    if get_settings().seed_demo and get_settings().demo_content:
        from app.services import demo_data  # after the connection above is closed
        demo_data.seed_content()
