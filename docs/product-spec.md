# Product spec (decisions made while building)

- **Dates:** an offer is valid *through the end of* its `valid_until` day, India time (IST). Checked on that date = valid; the next day = expired. Set `EVAL_DATE` or pass `evaluation_date` for reproducible runs.
- **Two date checks:** `expired_offer` (today is past the validity date) and `date_conflict` (the draft states a date later than the approved date) are separate findings.
- **Claims:** detection of ranking/superlative phrases is deterministic (`rule_engine.detect_claims`); the AI (or the offline heuristic) only judges support. No evidence in the kit => `Unverified`, never `False`.
- **Quote normalisation** (`text_utils.norm`): Unicode NFKC, smart quotes/dashes to ASCII, soft hyphens removed, hyphen+line-break joined, whitespace collapsed, case-folded.
- **Human control:** extracted rules are candidates until an admin confirms. Approval is by a reviewer other than the author, for one exact version. Approving with open high-severity findings needs a reason, recorded as an override.
- **Retention default:** uploaded files are processed in memory and **not stored**; only extracted text and confirmed rules are kept. With `LLM_API_KEY` set, extracted text and drafts are sent to the external LLM provider; with it empty nothing leaves the server.
- **Out of scope in this build:** OCR, Insights, integrations, publishing, vector search.

## Added in v1.1
- **Authentication:** email + password (scrypt hashes), signed expiring tokens, per-organisation isolation, admin-managed team. Swap for Supabase Auth by replacing `user_from_token`.
- **Images:** attached to a draft version; alt text, text/background contrast (WCAG ratio) and dominant-colour palette checks run only when the Brand Kit has an accessibility or palette rule. Only a 240 px thumbnail is stored. Palette matching is approximate and advisory; a match does not prove an image is on-brand.
- **Insights:** computed only from recorded events. A rule is flagged "possibly unclear" when it was shown at least 3 times and dismissed in at least half of them. Repeated runs on the same version are not double counted.
- **Claim support (offline mode):** a claim counts as supported only if every distinctive word of the claim appears in an approved fact; the AI-validation path requires at least half the claim's words to appear in the cited source.

## Roles (v1.3): who does what
- **Admin** owns Brand Kits (upload, confirm, send to creators, make inactive, delete if unused), the team and insights. Read-only on posts.
- **Creator** writes and submits posts. Creators never run checks and never see unflagged findings: the server filters findings by role. They fix what the reviewer flagged and resubmit.
- **Reviewer** presses **Start review** (Brand Kit rules, image checks, AI if on), flags real problems or dismisses false alarms, adds suggestions or edits the post, and decides. Approval needs the review to have been started; approving with open or flagged high-severity findings needs a reason.
- The first reviewer to start an unassigned post claims it. A resubmission must contain a change since the reviewer sent it back.
