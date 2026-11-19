# MatchPoint: Intelligent Resume–Job Matching System

A web-based Applicant Tracking System (ATS) that parses PDF resumes, compares them with a job description, and produces an **explainable match score** with matched and missing skills. Applications are then routed by the brief's **80% threshold and candidate-consent (Auto Apply) rules**.

**Stack:** React + Vite + Tailwind CSS · FastAPI · PyMuPDF · skill dictionary NLP · Sentence Transformers (all-MiniLM-L6-v2) with a TF-IDF fallback · SQLite (set `DATABASE_URL` for PostgreSQL).

---

## Quick start (Windows / PowerShell)

### Option A: one command (production-style, single server)
```powershell
.\run.ps1
```
Open http://localhost:8000. The script creates the venv, installs packages, builds the React app and serves everything from FastAPI.

### Option B: development (hot reload)
Terminal 1, backend:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt -r requirements-embeddings.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
Terminal 2, frontend:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (Vite proxies `/api` to port 8000). API docs: http://localhost:8000/docs

On first start the backend downloads the embedding model (~90 MB, once) and seeds **3 sample jobs + 12 demo candidates** (fictional, stored in `backend/data/demo_resumes/`). Set `SEED_DEMO=0` to start empty.

> Without `sentence-transformers` installed, the app still works and uses TF-IDF similarity automatically.

---

## Two separate portals

The candidate portal and the HR dashboard are fully separate: different sign-in pages, separate sessions, and no links between them.

- **Candidates** sign in at `/login` (or register at `/register`).
- **HR staff** sign in at `/hr/login`. This address isn't linked from anywhere candidates see; give it to HR staff directly.

Each sign-in page only accepts its own kind of account. Using the other kind gives the same "Incorrect email or password" message as a wrong password, so neither page reveals which accounts exist. The API enforces the same rules. Because the sessions are separate, one browser can have an HR tab and a candidate tab open without one signing the other out.

| | **Candidate portal** (`/portal`) | **HR dashboard** (`/`) |
|---|---|---|
| Sign in | `/login` (register at `/register`) | `/hr/login`: accounts created by an admin |
| What | **Jobs** (open jobs + Apply) · **My Resume** (upload/replace PDF) · **My Scores** (score + AI explanation) | Everything: dashboard, jobs, candidates, matching, applications, reports, settings |
| Sees | Only their own resume and scores | All candidates, queues, notes, decisions |
| Consent | Gives consent and Auto Apply when applying | Sees consent read-only; cannot set it on a candidate's behalf |

**Demo accounts** (created when `SEED_DEMO=1`; see `DEMO_ACCOUNTS` in `backend/app/seed.py`):
- HR: `hr@matchpoint.test` / `hr-demo-2026`
- Candidate: `rahul.kumar@example.com` / `candidate-demo-2026`

### Setting up real accounts

Run these from the `backend` folder with the server **stopped**.

**1. Turn off demo mode.** Copy `.env.example` to `.env` and set `SEED_DEMO=0`. Otherwise the demo accounts come back on every start.
```powershell
Copy-Item .env.example .env
```

**2. Pick a starting point:**
- *Fresh, empty system (recommended for real use):* delete the `data` folder. It holds the database, uploaded resumes and the session key, and is recreated empty on the next start.
- *Keep the demo jobs/candidates:* keep `data` and just delete the demo logins (step 4).

**3. Create your HR account(s).** HR can never self-register. The password is typed at a hidden prompt.
```powershell
.\.venv\Scripts\python -m app.users create-hr --email you@company.com --name "Your Name"
```

**4. Manage accounts.**
```powershell
.\.venv\Scripts\python -m app.users list
.\.venv\Scripts\python -m app.users set-password --email someone@company.com
.\.venv\Scripts\python -m app.users delete --email hr@matchpoint.test
```
The last HR account can't be deleted, so you can't lock yourself out.

**5. Candidates** create their own accounts at `/register`. Nothing to do on your side.

Alternative to step 3: set `HR_EMAIL`, `HR_PASSWORD` and `HR_NAME` in `.env` to create the first HR account on startup, then remove the password from the file.

**Security:** passwords are hashed with PBKDF2-SHA256 (240k rounds); sessions are HMAC-signed, httpOnly, SameSite=Lax cookies (7 days; key in `backend/data/secret.key` or `SECRET_KEY`); failed logins are rate limited (8 per 15 min); API responses are `no-store`.

---

## Account options

Both portals' account menu (top right) has **Change password**: it needs the current password and signs the account out on other devices. Candidates also have **Delete my account**, which permanently removes their account, resume file, profile and all scores and applications (password and typing DELETE required).

## Forgot password (email codes)

Both sign-in pages have a **Forgot password?** link (`/forgot-password` for candidates, `/hr/forgot-password` for HR). The person enters their email, gets a **6-digit code** by email, and sets a new password.

- Codes expire after 10 minutes and are single-use. After 5 wrong tries the code stops working.
- One code request per minute, at most 5 per hour, per email.
- The page answers the same way whether or not the email has an account, so nobody can probe for accounts.
- Each portal only resets its own accounts (a candidate email on the HR page gets no code).
- Changing the password signs the account out everywhere.

**Sending real email.** Set the `SMTP_*` variables (in `backend/.env`, or in your host's settings). With Gmail:
1. Turn on 2-Step Verification for the Google account.
2. Create an App Password at https://myaccount.google.com/apppasswords.
3. Set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USERNAME=<your gmail>`, `SMTP_PASSWORD=<the 16-character app password>`, `SMTP_FROM=MatchPoint <your gmail>`.

Any provider works the same way (Outlook, Brevo, SendGrid, Mailgun, Amazon SES). For a public site, a transactional provider with your own domain is better than Gmail (Gmail allows about 500 emails a day).

**Without SMTP settings:** in development the code is printed in the backend's console window, so you can test the flow. In production no email is sent.

Accounts must have a **real mailbox** to receive codes. Addresses like `@matchpoint.test` can't receive email; reset those with `python -m app.users set-password`.

## Workflow (as in the brief)

| Step | Where |
|---|---|
| 1. Recruiter creates a job with skills, experience, education | **Jobs → Create New Job** |
| 2. Candidate uploads a PDF and applies with consent | **Candidate portal → Jobs → Apply** (HR can also bulk-upload resumes for screening) |
| 3. Text extraction; skills, education, experience parsed | `services/parser.py` (PyMuPDF) |
| 4. Resume compared with the selected job | `services/matcher.py` + `services/semantic.py` |
| 5. Score + matched/missing skills + explanation | **Resume Matching** / **Candidate Insight** |
| 6. Submitted or routed for review by the rules below | **Applications** |

### Scoring (0–100, job-related criteria only)
| Component | Weight |
|---|---|
| Required skills matched | 50 |
| Preferred skills matched | 10 |
| Experience vs. minimum | 20 |
| Semantic fit (embeddings of JD ↔ resume) | 15 |
| Education level vs. minimum | 5 |

If a job has no preferred skills or no education requirement, that weight moves to required skills. Every score is shown with its per-component breakdown.

### Routing rules
- **≥ 80%, high match:** auto-submitted **only if** the candidate enabled Auto Apply **and** reviewed their details **and** consented to data sharing. Auto Apply on but a step missing → **Pending Consent**. Auto Apply off → **Recruiter Review**.
  Consent is **per job**: it's given when the candidate applies to that job, and never carries over. A high match that HR found by screening (the candidate didn't apply to that job) always goes to **Recruiter Review**.
- **60–79%:** **Recruiter Review**.
- **< 60%:** **Standard Review**.
- Recruiters make the final decision (**Shortlist / Reject**). Those decisions are kept when matching is re-run, and can be undone.
- Submission is **simulated**. Nothing is sent to an external ATS.

### Fairness
- Protected characteristics (age, gender, caste, religion, disability, photo, marital status) are never extracted, stored or scored.
- Recruiters and candidates can **correct parsing errors** (skills, experience, education) on the candidate profile; affected matches are re-scored right away.

---

## Demo script (covers every minimum deliverable)
1. **Dashboard:** totals, average score and match distribution.
2. **Resume Matching:** pick *Python Backend Developer* → **Run Matching** → click a candidate to see the explanation, breakdown and missing skills.
3. **80% threshold + consent:**
   - *Vikram Singh / Rahul Kumar* (≥ 80%, all consent given) → **Submitted**
   - *Priya Sharma* (≥ 80%, Auto Apply on, consent missing) → **Pending Consent**
   - Sign in as the demo candidate → **Jobs → Apply** with Auto Apply on → the HR **Applications** page shows it as **Submitted** when the score is ≥ 80%.
4. **Upload:** in the candidate portal, **My Resume** → drop a PDF from `backend/sample_resumes/`.
5. **Parsing correction:** open a candidate → **Correct** → add a missing skill → the score updates.
6. **Applications** queues and **Reports** (score histogram, applications by job, skill gaps, parse/match timings).

---

## Deploying online

MatchPoint ships as **one Docker container** that serves the React app and the API on one port. It's been checked in production mode (`APP_ENV=production`): API docs hidden, security headers on every response, login cookies `Secure` and `HttpOnly`, HSTS behind HTTPS, and no demo data.

### What any host needs
| Need | Why |
|---|---|
| **HTTPS** | Production login cookies are HTTPS-only. Every platform below gives HTTPS automatically. |
| **Persistent disk mounted at `/data`** | Holds the database, uploaded resumes and the session key. Without it, everything is lost on restart. |
| **≥ 1 GB RAM** | The AI embedding model uses ~700 MB. On a 512 MB plan, build with `WITH_EMBEDDINGS=false` (TF-IDF matching, ~150 MB). |
| **One instance only** | SQLite and the login rate limiter live in one process. Don't scale to multiple replicas. |

### Try the container locally (Docker Desktop must be running)
```powershell
docker build -t matchpoint .
docker run --rm -p 8000:8000 -v matchpoint-data:/data matchpoint
```
Open http://localhost:8000/hr/login. Create the first HR account inside the container:
```powershell
docker run --rm -it -v matchpoint-data:/data matchpoint python -m app.users create-hr --email you@company.com --name "Your Name"
```

### Option 1: Railway or Render (from GitHub)
1. Push this folder to a **private** GitHub repository.
2. Create a new service from the repo; the platform detects the `Dockerfile`.
3. Add a **volume / persistent disk** mounted at `/data`.
4. Set variables: `APP_ENV=production`, plus `HR_EMAIL` and `HR_PASSWORD` for the first HR account (remove the password variable after first start).
5. Deploy, then open `https://<your-app>/hr/login`. `/api/health` is the health-check path.

If the logs say *"cannot write to its data folder /data"*, the platform mounted the disk as root-only: set its "run as root" option, or mount the disk at a writable path and set `DATA_DIR` to it.

### Option 2: Fly.io
`fly launch` (it detects the Dockerfile), then `fly volumes create matchpoint_data --size 1` and add to `fly.toml`:
```toml
[mounts]
  source = "matchpoint_data"
  destination = "/data"
```
Use a machine with at least 1 GB memory.

### Option 3: Your own server (VPS)
Install Docker, copy the project, then `docker compose up -d --build`. The compose file only opens port 8000 to the server itself, on purpose: the app trusts the proxy's `X-Forwarded-*` headers, so all public traffic must come through your HTTPS proxy. Put Caddy or Nginx in front for HTTPS (Caddy does it automatically with one line: `matchpoint.yourdomain.com { reverse_proxy localhost:8000 }`).

### After deploying
- **Back up `/data`** regularly (database + resumes). Copying the folder while the app is stopped is enough.
- **Monitor** `https://<your-app>/api/health` with a free uptime checker.
- Keep `SEED_DEMO` unset (off) in production, so no demo accounts exist.

## Efficiency notes
- Embedding model loaded **once** at startup; embeddings **cached by text hash**, so re-matching only encodes new or changed resumes. Matching a job against all candidates is a single **batched** encode (~300 ms for 13 resumes on CPU).
- Duplicate resumes are detected by SHA-256 and skipped.
- SQLite in WAL mode; indexed status, score and foreign-key columns; eager loading (no N+1 queries).
- Frontend: route-level code splitting (main bundle ~90 KB gzipped); charts load only on pages that use them; gzip responses.

## Sample resumes to upload

`backend/sample_resumes/` has **10 one-page resumes** for fictional people, in six layout styles like the ones on resume-template websites: classic, dark sidebar, colour banner, label column, timeline and skill bars. The roles cover Python backend, frontend React, data analyst, DevOps, ML engineer, fresher, full stack (MERN), senior Java, QA automation and data engineering.

Upload them as HR (**Upload Resumes**, several at once) or as a candidate (**My Resume**). To regenerate them:
```powershell
cd backend
.\.venv\Scripts\python scripts\make_sample_resumes.py
```
The test suite parses every sample and checks name, email, experience, degree and key skills.

## Resume parsing: what it handles
- **Skills:** ~200 skills with aliases (k8s → Kubernetes, sklearn → Scikit-learn). Ordinary English words only count with the right capitalisation ("Excel", "Express", "Spark"), and single letters (C, R, Go) only count inside a skill list. Implied skills are added automatically (Django → Python, Jenkins → CI/CD, MySQL → SQL).
- **Experience:** "Jan 2021 – Present", "06/2021 – 08/2023", "06-2021 to 08-2023", "Jan '21", "2019-2021", or an explicit "5+ years of experience". Overlapping jobs are merged; education and project dates are ignored; works with or without an "Experience" heading.
- **Known limits:** scanned/image PDFs need OCR (not included); heavily designed two-column templates can scramble text order; a score shows a skill is *mentioned*, not how strong it is. Fix any parsing error with **Correct** on the candidate profile.

After upgrading the parser, re-parse stored resumes (manually corrected profiles are left alone):
```powershell
cd backend
.\.venv\Scripts\python -m app.seed --reparse
```

## Tests
```powershell
cd backend
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```
Covers parsing (skill boundaries, degrees, overlapping experience ranges), the end-to-end flow, consent routing, corrections, recruiter decisions, upload validation and job edits.

## Project layout
```
backend/
  app/main.py            FastAPI app, startup (model load, seed), serves built frontend
  app/api.py             HR-only REST endpoints (jobs, candidates, upload, match, applications, stats, reports)
  app/auth.py            login/register, password hashing, signed session cookies, role guards
  app/portal.py          candidate portal endpoints (jobs, own resume, apply, own scores)
  app/users.py           CLI: create HR accounts
  app/models.py          Job, Candidate, Application (SQLAlchemy)
  app/services/parser.py PDF text, contact, skills, education, experience
  app/services/skills.py skill dictionary (~200 skills, aliases, implied skills)
  app/services/semantic.py embeddings / TF-IDF similarity with cache
  app/services/matcher.py  scoring, explanation, routing rules
  app/seed.py            sample jobs + generated sample resumes
  tests/test_api.py
frontend/src/
  pages/                 Login/Register, HR pages, portal/Portal (candidate portal)
  components/            MatchTable, InsightPanel, UploadModal, JobForm, SkillInput, ui
```

## Configuration (env vars)
| Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite in `backend/data/` | e.g. `postgresql+psycopg://user:pass@host/db` |
| `SEMANTIC_ENGINE` | `auto` | `auto`, `embeddings` or `tfidf` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | any Sentence Transformers model |
| `APP_ENV` | `development` | `production` = Secure cookies, API docs hidden, demo data off (set automatically in the Docker image) |
| `SEED_DEMO` | `1` in development, `0` in production | seed sample data and demo accounts when the DB is empty |
| `COOKIE_SECURE` | `auto` in development, `true` in production | force session cookies to HTTPS-only (`true`/`false`/`auto`) |
| `ENABLE_DOCS` | on in development, off in production | interactive API docs at `/docs` |
| `DATA_DIR` | `backend/data` (`/data` in Docker) | database, uploaded resumes, session key |
| `SMTP_HOST` / `SMTP_PORT` | none / `587` | mail server for password-reset codes |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | none | mail server login (Gmail: an App Password) |
| `SMTP_FROM` | `SMTP_USERNAME` | sender, e.g. `MatchPoint <you@gmail.com>` |
| `SMTP_SECURITY` | `starttls` | `starttls` (port 587), `ssl` (port 465) or `none` |
| `CORS_ORIGINS` | `http://localhost:5173,...` | allowed frontend origins |
| `SECRET_KEY` | generated into `backend/data/secret.key` | signs session cookies |
| `HR_EMAIL` / `HR_PASSWORD` / `HR_NAME` | unset | create the first HR account on startup |
