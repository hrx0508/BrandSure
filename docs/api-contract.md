# API contract (v1.3)

Base: `/api/v1`. JSON, except uploads (multipart). Auth: `Authorization: Bearer <token>` from `POST /auth/login`.
Errors: `{"error": {"code", "message", "request_id"}}`.

| Method + endpoint | Purpose | Role |
|---|---|---|
| GET /health | Liveness, AI mode and disclosure text (+ demo accounts in development only) | public |
| POST /auth/login, POST /auth/register | Sign in / create an organisation (caller becomes admin) | public |
| GET /auth/me | Current user | any |
| GET /users, POST /users | List / add people in your organisation | admin |
| POST /brand-kits/extract, POST /brand-kits/extract-google-doc | Upload PDF/DOCX (scans use OCR) or import a Google Doc; get candidate rules | admin |
| GET /brand-kits, GET /brand-kits/{id} | List / detail (+ pending extraction for admin) | any member |
| POST /brand-kits/{id}/confirm | Save confirmed rules as a new version | admin |
| POST /brand-kits/{id}/publish | Send the confirmed kit to creators | admin |
| POST /brand-kits/{id}/deactivate, /activate, DELETE /brand-kits/{id} | Make inactive / active again / delete (only if no posts use it) | admin |
| GET /brand-kits/{id}/versions | Version list | admin, reviewer |
| GET /overview, GET /reviews, GET /insights | Counts / list / governance insights from real events | any member |
| POST /reviews, /reviews/upload, /reviews/from-google-doc | Create a post from text / DOCX or PDF / Google Doc (kit must be live) | creator |
| GET /tasks | Role-specific to-do list and what the person is waiting for | any |
| GET /reviewers, GET /integrations | Reviewers to send to / which optional services are on | any / admin |
| GET /reviews/{id}?version_number= | Review, versions, findings, images, decisions, comments | any member |
| POST /reviews/{id}/start-review | Run Brand Kit, image and AI checks on the submitted version (`rerun` to repeat). Claims the post if unassigned | reviewer |
| POST /reviews/{id}/findings/{fid}/triage, POST /reviews/{id}/triage-all | `flag` (show to creator) / `dismiss` / `reopen`; flag all open findings | reviewer |
| POST /reviews/{id}/findings/{fid} | accept / edit / mark fixed / undo on a finding the reviewer flagged (cannot dismiss) | creator (owner) |
| GET /my-feedback | Flag counts across the creator's own posts, for charts | creator |
| POST /reviews/{id}/revisions | Save a new version (old kept, images carried forward) | creator (owner) |
| POST/PATCH/DELETE /reviews/{id}/images[/{iid}] | Attach image (max 5), edit alt text and colours, remove | creator (owner) |
| POST /reviews/{id}/request-review | Submit to a reviewer (`reviewer_id` optional). A resubmission needs a change since the reviewer sent it back | creator (owner) |
| POST /reviews/{id}/mark-published | Record that an approved post went live | creator (owner) |
| POST /reviews/{id}/images/{iid}/suggest-alt | Optional AI alt-text suggestion | creator (owner) |
| POST /reviews/{id}/suggestions | Suggest replacement text for a selected range | reviewer |
| POST /reviews/{id}/reviewer-edit | Edit the post (new version, goes back to the creator) | reviewer |
| POST /reviews/{id}/decision | `approve` / `request_changes` / `reject` for a specific `version_number` | reviewer (not the author; the assigned one if any) |
| POST /reviews/{id}/comments, GET /reviews/{id}/audit | Comments / history | members |

Visibility: creators only receive findings with status flagged / accepted / edited / resolved. Finding statuses: open (reviewer only), flagged, dismissed, accepted, edited, resolved.
Finding types: terminology, banned_term, expired_offer, date_conflict, missing_disclaimer, unsupported_claim, tone_mismatch, visual_palette, missing_alt, low_contrast, other.
Evidence status: approved_rule, verified, not_found, invalid_citation, quote_invalid, weak_support.
Review statuses: draft, in_review, changes_requested, approved, published, rejected. Kit states: needs_confirmation, ready_to_send, live, inactive.
Codes: KIT_NOT_PUBLISHED, KIT_INACTIVE, KIT_IN_USE, AI_NOT_CONFIGURED, GDOC_NOT_SHARED, INVALID_URL, NO_PROFILE (all 4xx); UNAUTHENTICATED 401, INVALID_CREDENTIALS 401, FORBIDDEN 403, NOT_FOUND 404, EMAIL_TAKEN 409, INVALID_STATE 409, REVIEW_NOT_STARTED 409, ALREADY_STARTED 409, NO_CHANGES 409, STALE_VERSION 409, KIT_NOT_CONFIRMED 409, TOO_MANY_IMAGES 409, UNSUPPORTED_FILE_TYPE / UNSUPPORTED_IMAGE / EMPTY_DOCUMENT / CORRUPT_FILE 400, FILE_TOO_LARGE 413, VALIDATION_ERROR / REASON_REQUIRED / OVERRIDE_REASON_REQUIRED 422, RATE_LIMITED 429.
