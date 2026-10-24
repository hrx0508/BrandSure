# BrandSure

Explainable pre-publication brand governance. Admins confirm a **Brand Kit** from their guidelines; creators check drafts (text, documents and images) against it; every finding shows its rule or source, uncertainty and a suggested fix; a **reviewer** approves one exact version. Governance insights show repeated mistakes and rules that may be unclear.

Stack: React + Vite + Tailwind + GSAP, FastAPI + Pydantic, SQLite for local development (PostgreSQL migration included), PyMuPDF, python-docx, Pillow. Optional: AI provider, Slack, Tesseract OCR, Google Docs import, Supabase Auth (blank sections in `backend/.env.example`; guide in `docs/INTEGRATIONS.md`).

## Run it

```bash
# Terminal 1 - backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                    # edit: SECRET_KEY and any blanks you want (see docs/INTEGRATIONS.md)
uvicorn app.main:app --reload --port 8000

# Terminal 2 - frontend
cd frontend
cp .env.example .env
npm install
npm run dev                                             # http://localhost:5173
```

**One-click demo:** open the login page and press **Enter** on Admin, Creator or Reviewer. Sample data is already loaded (a live TechNova Brand Kit; a draft for the creator to submit; a submitted post for the reviewer to start; and a post the reviewer already sent back with red flags for the creator to fix). A bar at the top lets you switch role or **Reset demo data**. Manual demo logins: `admin@`, `creator@`, `reviewer@brandsure.demo`, password `brandsure123`. Or choose **Create organisation** to start your own.

Demo access is on by default in development. To keep it on for a shared demo deployment set `DEMO_LOGIN=true`; with `APP_ENV=production` it is off unless you set that, and a real `SECRET_KEY` is required. Turn it off with `DEMO_LOGIN=false` and `SEED_DEMO=false` for real use.

## Roles and the workflow

Each role has its own screen and its own job. Nobody does another role's work.

| Role | Does | Never does | Waits for |
|---|---|---|---|
| **Admin** | Uploads guidelines (PDF, DOCX, scanned PDF, Google Doc), confirms the rules, **sends the Brand Kit to creators**, makes a kit inactive or deletes an unused one, adds people | Create or review posts | Creators to use the kit |
| **Creator** | **Creates a post** and submits it to a reviewer; then sees **only what the reviewer flagged** (with charts), fixes it and resubmits; marks the approved post as published | Run checks, see unflagged findings, approve | The reviewer |
| **Reviewer** | Presses **Start review** (Brand Kit + image + AI checks), **flags** real problems and **dismisses** false alarms, suggests changes or edits the post, then **approves / sends back with flags / rejects** | Create posts | The creator's fixes |

The loop: Admin sends kit > Creator creates and submits a post > Reviewer starts the review, flags, suggests or edits, decides > Creator sees the flags, fixes, resubmits > Reviewer confirms > Approved > Creator publishes and marks it. Each post shows a process tracker ("Your move" or "Waiting for ..."), and Home shows each person their own to-do and waiting lists. The in-app page *How it works* lists what each role can and cannot do.

## Try it (fictional TechNova)

With the one-click demo each role already has work waiting. To go through the whole loop yourself:

1. **Admin:** Brand Kits > drop `samples/technova_guidelines.docx` > check the rules and their source quotes > **Confirm** > **Send to creators**.
2. **Creator:** **Create post** > paste `samples/sample_draft.txt` (or upload a DOCX / import a Google Doc) > attach an image > **Submit to reviewer**. You see nothing flagged yet: the reviewer has not looked.
3. **Reviewer:** open it from your to-do > **Start review** > go through the findings: **Flag for creator** or **Dismiss**, add a suggestion or edit the post > **Send back with flags** (or Approve / Reject).
4. **Creator:** your post now shows the red flags with charts. Accept suggestions or edit the text, save, **Resubmit**. **Reviewer:** Start review again > **Approve**. **Creator:** **Mark as published**.
5. **Reviewer / Admin:** Insights shows charts built from those events.

## AI and privacy

With `LLM_API_KEY` empty, checks run on your server only. With a key, extracted guideline text and drafts are sent to the configured LLM provider; every AI answer is validated (structure, source IDs, quotes, text positions) and unsupported claims show as **Unverified**. The app shows this disclosure in the footer and on the login page. Uploaded files are processed in memory and not kept; only extracted text, confirmed rules and 240 px image thumbnails are stored.

## Tests

```bash
cd backend && pytest
```

## Verification status (please read)

Built and checked in an offline sandbox with no package installs, so:
- **Run for real:** the rule engine, evidence validator, extractors, OCR branching (with a fake PDF), image checks, token/password code, Supabase JWT verification, Google Docs URL checks, insights and the labelled evaluation set (42 tests).
- **Run against stand-ins:** the API routes and `tests/test_api.py` (8 end-to-end scenarios: auth, organisation isolation, kit publish/deactivate/delete, the creator-reviewer loop where findings stay hidden from the creator until the reviewer flags them, suggestions, reviewer edits, reject, publish, tasks, insights) were executed with a small throwaway FastAPI/pydantic stand-in that is not included. The real FastAPI and Pydantic have not run this code, so expect small integration fixes on first start.
- **Not run:** calls to Slack, Google, Supabase and the AI provider; real Tesseract OCR; `npm install`, `vite build`, and the animations in a browser. The React code passes syntax and import checks, its components render with React's server renderer, and the "whose move is it" logic was tested for every status and role.
- Rate limits are per process. Set `SECRET_KEY` before any shared deployment.

## Not built yet

Moving application data to Supabase PostgreSQL (sign-in can already use Supabase), Canva, video/audio, multilingual review, direct publishing. See `docs/` for the API contract, schema, product decisions and test plan.
