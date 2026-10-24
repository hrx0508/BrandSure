# Integrations: what to fill in

Everything here is optional. Add values to `backend/.env`, restart the backend, then open **Integrations** in the app (admin) to see what is on. A ready-made template with blanks is `backend/.env.example`.

## 1. AI (the blank you asked for)
BrandSure uses AI in three places, and only these:
1. **Tone and claim judgement** on drafts (every answer is validated against the Brand Kit before it is shown).
2. **Proposing rules** from uploaded guidelines (the admin confirms every rule).
3. **Alt-text suggestions** for attached images (the creator edits the result).

Fill in:
```
LLM_API_KEY=<your key>
LLM_MODEL=claude-sonnet-5-5        # or any model your provider offers
LLM_URL=https://api.anthropic.com/v1/messages
```
The code calls the Anthropic Messages API format. Without a key, offline checks run and nothing is sent anywhere. With a key, guideline text, drafts and (for alt text) a 240 px thumbnail are sent to the provider; the app says so in the footer and on the login page.
Code lives in `backend/app/services/llm.py` (provider hidden behind two functions).

## 2. Slack notifications
1. In Slack: Apps > Incoming Webhooks > create a webhook for a channel.
2. `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...`

Messages contain titles and statuses only, never draft text. Sent when: a kit is sent to creators, a post is sent for review, and a reviewer approves, sends back, edits or rejects. Code: `backend/app/services/notify.py`.

## 3. Google Docs import
Nothing to fill in. Share the doc as **Anyone with the link can view**, then paste its link when uploading guidelines or starting a post. Only text is imported. For private docs, download as DOCX and upload that. Code: `backend/app/services/gdocs.py`.

## 4. OCR for scanned PDFs
Scanned pages have no selectable text, so they are read as images.
- Install the **Tesseract** program (Windows: the UB-Mannheim installer, and add it to PATH; macOS: `brew install tesseract`; Ubuntu: `sudo apt install tesseract-ocr`).
- `pip install -r backend/requirements-optional.txt`
- Restart. `OCR_LANG` selects the language (`eng`, `hin`, ... needs that language pack).

Up to 30 pages per file are read with OCR. The admin is warned which pages used OCR because OCR can misread words and numbers. Without Tesseract, a scanned PDF fails with a clear message.

## 5. Supabase Auth
1. Create a Supabase project. In Project Settings > API copy the project URL, `anon` key, `service_role` key and (optional) JWT secret.
2. Fill `AUTH_PROVIDER=supabase`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_JWT_SECRET` if your project uses the legacy HS256 secret. If it uses asymmetric signing keys, leave the secret empty and BrandSure asks Supabase to verify each token (cached for 60 seconds).
3. Sign in and registration now go through Supabase; admins creating people use the Supabase admin API. Roles and organisations stay in BrandSure's `profiles` table (keyed by the Supabase user id).
4. The first admin: use **Create organisation** on the login page. Turn on email confirmation in Supabase if you want it; the page will then ask the person to confirm and sign in.

Important: this switches **sign-in only**. Application data still lives in the local SQLite file. Moving data to Supabase PostgreSQL means applying `supabase/migrations/0001_init.sql` and replacing the data layer in `backend/app/repositories/store.py`; that step is not done.
Code: `backend/app/services/supabase_auth.py`, `backend/app/core/security.py`, `backend/app/api/v1/auth.py`.

## Not tested against live services
These integrations were written and unit-tested without internet access (token checks, URL parsing, OCR branching and fallbacks are tested; calls to Slack, Google, Supabase and the AI provider were not). Test each once with your own credentials.
