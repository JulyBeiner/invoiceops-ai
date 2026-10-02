# InvoiceOps

**Month-end close in 10 minutes for service companies.** InvoiceOps is the pre-billing layer for small B2B cleaning and maintenance companies in Spain: record the work done for each client during the month, apply each client's contract, and get one billing proposal per client — reviewed, approved, exported as PDF for the client and CSV for the accounting tool.

It deliberately does **not** issue legal invoices (Verifactu makes invoicing software a regulated product from 2027): it produces billing proposals that any invoicing tool or accounting firm can turn into invoices. The PDF says so in its footer.

Capstone project of the 4Geeks Academy full-stack bootcamp, built solo by July Beiner. **Live demo: https://invoiceops-vs2v.onrender.com** (free tier: the first load can take a minute) — demo account `july@limpiezasaurora.es` / `Aurora2026!`.

## The flow

1. **Register** the company and its owner.
2. **Clients and contracts**: fixed monthly fee, VAT and a price per service (a catalog of standard services of the niche can be added in one click). The AI can read the text or a photo of the contract and prefill those fields for review.
3. **Activities**: what was done, for whom, when and how much — typed one by one, imported from a CSV (Spanish Excel formats accepted: `;`, `3,5`, `10/09/2026`; names matched even with typos), or captured with AI from pasted WhatsApp messages, a photo of a work sheet or a voice note.
4. **Month close**: the billing engine builds one proposal per client from the activities and the contract.
5. **Review and approve** each proposal: every line links to the activities behind it; the AI can explain it in plain words and draft the email for the client. Download the PDF, export the approved proposals as CSV.

The AI reads and proposes; the billing engine computes; the person confirms. The AI never touches a price or a total, and nothing it suggests is saved until the person confirms it.

## The AI features

| Feature                      | Where                                                  | What the AI does                                                                                                   |
| ---------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Capture activities from text | Actividades → "Sugerir con IA"                         | reads pasted WhatsApp messages or notes and proposes activities (client, service, date, quantity) as editable rows |
| Capture from a photo         | same panel, file input                                 | reads a photo of a work sheet, a handwritten note or a chat screenshot                                             |
| Capture from a voice note    | same panel, file input                                 | transcribes the audio (`.m4a`, `.ogg`, `.mp3`…) and proposes activities from the transcript                        |
| Contract from text or photo  | Clientes → ficha → "Rellenar con IA desde el contrato" | reads a contract or quote and prefills fee, VAT and prices; offers to create the services it does not know         |
| Explain a proposal           | Propuesta → "Explicar con IA"                          | plain-language summary of the proposal and a draft email for the client, using the engine's figures verbatim       |

Every AI endpoint returns suggestions only; the backend re-matches names, re-parses dates and numbers, and nothing is written until the person confirms through the normal endpoints. Prompts are in Spanish, ask for JSON only, and carry the facts (dates, names, amounts) so the model never computes. Provider: OpenAI (`gpt-5.4-mini`, `whisper-1`), called through REST; model names can be overridden with `AI_MODEL` / `AI_AUDIO_MODEL`.

## Stack

- **Backend**: Python 3.13, Flask 3, SQLAlchemy 2, Alembic (Flask-Migrate), PostgreSQL 16, JWT (flask-jwt-extended), bcrypt, fpdf2 for the PDF, Brevo API for the password-reset email, OpenAI API (REST, no SDK) for the AI features. Multi-tenant: every table carries `tenant_id` and every query filters by it. The billing engine (`src/api/services/billing.py`) is pure Python, separated from Flask, and the only place where prices and totals are computed. 83 pytest tests; AI calls are faked in tests.
- **Frontend**: React 18 + Vite, React Router, Context + reducer store, Bootstrap 5 with custom design tokens (`src/front/index.css`). Spanish UI.
- **Docs**: `docs/SPECS.md` (user stories, class diagram, API table), `docs/DESIGN.md` (palette, typography, screens).

## Run it locally

Requirements: Python 3.13 + Pipenv, Node 20, PostgreSQL (GitHub Codespaces has all three).

    pipenv install
    npm install
    cp .env.example .env        # then fill in the values (see below)
    pipenv run upgrade          # create the tables
    pipenv run seed             # load the demo company
    pipenv run start            # Flask API on :3001
    npm run start               # Vite dev server on :3000 (proxies /api to :3001)

Open http://localhost:3000 and log in with the demo account.

`.env` variables: `DATABASE_URL`, `FLASK_APP=src/app.py`, `FLASK_APP_KEY`, `FLASK_DEBUG=1`, `BREVO_API_KEY` and `MAIL_FROM` (password-reset email; optional in development), `FRONTEND_URL` (used in the reset link), `AI_PROVIDER` and `AI_API_KEY` (AI features; optional: without them the app works and the AI buttons say the AI is not configured).

### Demo data

`pipenv run seed` creates Limpiezas Aurora S.L. with three services, four clients with contracts (Farmacia Central has a contract and no activity, on purpose), 38 activities in September 2026 and 12 in early October. It does nothing if the company already exists; `pipenv run seed --reset` deletes it and loads it again. Two sample CSVs for the import dialog live in `docs/demo/`.

### Tests

    pipenv run pytest -q

Tests run against `TEST_DATABASE_URL` (default: the `example_test` database on localhost). Money and business rules were written test-first.

## API

All routes under `/api`; routes marked 🔒 need `Authorization: Bearer <token>`. Errors return `{"message": "..."}` with 400 / 401 / 404 / 409 (503 when the AI is not configured, 502 when the AI provider fails).

| Method             | Route                                           | What it does                                                              |
| ------------------ | ----------------------------------------------- | ------------------------------------------------------------------------- |
| POST               | `/auth/register`                                | create company + owner, returns token                                     |
| POST               | `/auth/login`                                   | returns token                                                             |
| GET                | `/auth/me` 🔒                                   | current user                                                              |
| GET / PUT          | `/auth/tenant` 🔒                               | company name and tax id                                                   |
| POST               | `/auth/forgot-password`, `/auth/reset-password` | password reset by email                                                   |
| GET / POST         | `/clients` 🔒                                   | list / create clients                                                     |
| GET / PUT / DELETE | `/clients/<id>` 🔒                              | detail with contract / edit / archive                                     |
| PUT                | `/clients/<id>/contract` 🔒                     | replace the contract (fee, VAT, prices)                                   |
| POST               | `/clients/<id>/contract/suggest` 🔒             | AI: contract proposal from text or a photo                                |
| GET / POST         | `/services` 🔒                                  | list / create services                                                    |
| GET / POST         | `/services/catalog` 🔒                          | standard services of the niche / create a chosen subset                   |
| GET / POST         | `/activities` 🔒                                | list (`?month=YYYY-MM&client_id=`) / create                               |
| POST               | `/activities/import` 🔒                         | CSV preview; `?commit=true` saves the valid rows                          |
| POST               | `/activities/suggest` 🔒                        | AI: activity suggestions from text, a photo or a voice note (never saves) |
| GET / POST         | `/billing-runs` 🔒                              | list / close a month (`{"month": "YYYY-MM"}`)                             |
| GET                | `/billing-runs/<id>` 🔒                         | run with its proposals                                                    |
| GET                | `/billing-runs/<id>/export.csv` 🔒              | approved proposals as CSV                                                 |
| GET                | `/proposals/<id>` 🔒                            | proposal with lines and activities                                        |
| POST               | `/proposals/<id>/approve` 🔒                    | approve; closes the run when all are approved                             |
| GET                | `/proposals/<id>/pdf` 🔒                        | proposal as PDF                                                           |
| GET                | `/proposals/<id>/explain` 🔒                    | AI: plain-language summary and client email draft                         |
| GET                | `/dashboard` 🔒                                 | counters and totals for a month                                           |

Full table with request bodies and user stories: `docs/SPECS.md`.

## Data model

    TENANT 1-n USER · TENANT 1-n CLIENT · TENANT 1-n SERVICE · CLIENT 1-1 CONTRACT · CONTRACT 1-n CONTRACT_PRICE (per SERVICE)
    CLIENT 1-n ACTIVITY (of a SERVICE) · TENANT 1-n BILLING_RUN 1-n PROPOSAL (per CLIENT) 1-n PROPOSAL_LINE 1-n ACTIVITY

The Mermaid diagram with every column is in `docs/SPECS.md`.

## Deploy (Render)

`render.yaml` is a Render Blueprint: one native Python web service (no Docker) and one PostgreSQL database, both in Frankfurt. Build: `render_build.sh` (npm install + build, pipenv install, migrations, demo seed — set `SEED_RESET=1` to reload the demo company on the next deploy); start: `gunicorn wsgi --chdir ./src/`. Flask serves the compiled React from `dist/` and the API from the same origin. Every push to `main` deploys. Secrets (`BREVO_API_KEY`, `MAIL_FROM`, `AI_PROVIDER`, `AI_API_KEY`) are set in the Render dashboard, never in the repo.

## Privacy and cost of the AI

Client names, the pasted messages and the uploaded files are sent to the AI provider to be analysed; at this volume each call costs cents. Without a key the application works fully and the AI buttons say so.

## Known limitations

- A month close cannot be undone or re-run: if an activity was missing, it will be billed in the next close.
- One active contract per client, without price history: changing a price applies from the next close.
- Roles (`owner`, `admin`, `operator`) are stored but not enforced yet: every user can do everything inside their own company.
- Access tokens last 12 hours and there is no refresh token: after that, log in again.
- The AI features depend on an external provider and are disabled when no key is configured.
- The demo account is shared: anyone can change its data; `SEED_RESET=1` reloads it on the next deploy.

## What comes next

Phase 2 of a real product: real WhatsApp Business connection (messages arrive without pasting), a review of the month before closing it (missing visits, unusual quantities), end-client approval and payment, accounting-firm channel, integrations with Holded / Quipu, and Verifactu-compliant invoicing only with traction.

Built on the [4Geeks React + Flask template](https://github.com/4GeeksAcademy/react-flask-hello).
