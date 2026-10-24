-- BrandSure schema for Supabase PostgreSQL (local development uses SQLite with the same shape).
-- Local development stores email + password_hash in `profiles`; on Supabase use Supabase Auth instead and drop those columns
-- (verify the Supabase JWT in backend/app/core/security.py: user_from_token).
-- Apply when moving off the local prototype. Backend keeps enforcing roles; RLS is defence in depth.
create extension if not exists "pgcrypto";

create table organisations (id uuid primary key default gen_random_uuid(), name text not null, created_at timestamptz not null default now());
create table profiles (user_id uuid primary key references auth.users(id), organisation_id uuid not null references organisations(id),
  role text not null check (role in ('admin','creator','reviewer')), display_name text not null);
create table brand_kits (id uuid primary key default gen_random_uuid(), organisation_id uuid not null references organisations(id),
  name text not null, active_version_id uuid, created_by uuid not null, created_at timestamptz not null default now(),
  status text not null default 'active' check (status in ('active','inactive')), published_at timestamptz, published_by uuid);
create table brand_kit_versions (id uuid primary key default gen_random_uuid(), kit_id uuid not null references brand_kits(id),
  version_number int not null, status text not null, confirmed_by uuid, confirmed_at timestamptz, created_at timestamptz not null default now(),
  unique (kit_id, version_number));
alter table brand_kits add foreign key (active_version_id) references brand_kit_versions(id);
create table brand_rules (id uuid primary key default gen_random_uuid(), version_id uuid not null references brand_kit_versions(id),
  type text not null check (type in ('preferred_term','banned_term','expiry','required_disclaimer','claim_rule','tone_guideline','fact','palette','accessibility')),
  title text not null, content text not null, severity text not null check (severity in ('low','medium','high')),
  valid_from date, valid_until date, params jsonb not null default '{}', source jsonb);
create table documents (id uuid primary key default gen_random_uuid(), organisation_id uuid not null references organisations(id),
  kit_id uuid not null references brand_kits(id), filename text not null, mime_type text, size_bytes bigint,
  status text not null check (status in ('uploaded','extracting','needs_confirmation','confirmed','failed')),
  extracted_text text, units jsonb, candidates jsonb, warnings jsonb, extraction_mode text, created_by uuid, created_at timestamptz not null default now());
create table reviews (id uuid primary key default gen_random_uuid(), organisation_id uuid not null references organisations(id),
  kit_id uuid not null references brand_kits(id), kit_version_id uuid not null references brand_kit_versions(id), title text not null,
  content_type text, status text not null check (status in ('draft','in_review','changes_requested','approved','published','rejected')),
  reviewer_id uuid, round int not null default 0,
  created_by uuid not null, created_at timestamptz not null default now(), updated_at timestamptz not null default now());
create table review_versions (id uuid primary key default gen_random_uuid(), review_id uuid not null references reviews(id),
  version_number int not null, content text not null, created_by uuid not null, created_at timestamptz not null default now(),
  analyzed_at timestamptz, analysis jsonb, unique (review_id, version_number));
create table findings (id uuid primary key default gen_random_uuid(), review_version_id uuid not null references review_versions(id),
  type text not null, severity text not null, verdict text, span jsonb, quoted_text text, explanation text, source_ids jsonb, source_refs jsonb,
  evidence_status text, suggested_fix text, replacement text, status text not null default 'open'
    check (status in ('open','accepted','edited','dismissed','resolved')),
  final_text text, origin text, requires_human_review boolean default true, uncertainty text, position int default 0, meta jsonb);
create table review_images (id uuid primary key default gen_random_uuid(), review_version_id uuid not null references review_versions(id),
  filename text not null, alt_text text, text_color text, bg_color text, width int, height int, dominant jsonb, thumb text,
  created_at timestamptz not null default now());
create table review_comments (id uuid primary key default gen_random_uuid(), review_id uuid not null references reviews(id), version_id uuid,
  author_id uuid not null, body text not null, created_at timestamptz not null default now());
create table approval_events (id uuid primary key default gen_random_uuid(), review_id uuid not null references reviews(id),
  version_id uuid not null references review_versions(id), reviewer_id uuid not null, decision text not null, reason text, created_at timestamptz not null default now());
create table audit_events (id uuid primary key default gen_random_uuid(), organisation_id uuid not null references organisations(id),
  actor_id uuid not null, action text not null, entity_id text, metadata jsonb, created_at timestamptz not null default now());
create index on reviews (organisation_id, status, created_at);
create index on audit_events (organisation_id, entity_id);

-- Row level security: enable and add organisation-scoped policies before exposing any table to the browser.
alter table organisations enable row level security; alter table profiles enable row level security;
alter table brand_kits enable row level security; alter table reviews enable row level security;
-- Example policy (repeat per table):
-- create policy org_isolation on reviews using (organisation_id = (select organisation_id from profiles where user_id = auth.uid()));
