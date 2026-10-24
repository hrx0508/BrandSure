# Database schema
See `backend/app/db/client.py` (SQLite, local prototype) and `supabase/migrations/0001_init.sql` (PostgreSQL target). Reviews are pinned to a `kit_version_id`; `review_versions` are immutable snapshots; every important action writes an `audit_events` row.
