import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from sqlalchemy import inspect, text

from . import auth, portal, settings
from .api import router
from .database import Base, SessionLocal, engine
from .services import semantic

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def migrate() -> None:
    """Create new tables and add columns introduced after the first release (SQLite-safe)."""
    Base.metadata.create_all(engine)
    if "auto_apply_all" not in {c["name"] for c in inspect(engine).get_columns("candidates")}:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN auto_apply_all BOOLEAN DEFAULT 0"))
    cols = {c["name"] for c in inspect(engine).get_columns("applications")}
    if "candidate_applied" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE applications ADD COLUMN candidate_applied BOOLEAN DEFAULT 0"))
    if "auto_apply" not in cols:
        # consent moved from the candidate profile to each application: copy it onto the
        # applications the candidate made themselves, then re-route everything not locked by HR
        with engine.begin() as conn:
            for col in ("auto_apply", "details_reviewed", "data_sharing_consent"):
                conn.execute(text(f"ALTER TABLE applications ADD COLUMN {col} BOOLEAN DEFAULT 0"))
                conn.execute(text(
                    f"UPDATE applications SET {col} = (SELECT c.{col} FROM candidates c "
                    "WHERE c.id = applications.candidate_id) WHERE candidate_applied = 1"))
        from .models import Application
        from .services.matcher import route

        with SessionLocal() as db:
            for a in db.query(Application).filter(Application.status_locked.is_(False)):
                route(a)
            db.commit()


def ensure_accounts(db) -> None:
    """Create the first HR account from env vars, and demo accounts when demo data is on."""
    from .auth import create_user
    from .models import Candidate, User

    hr_email, hr_pw = os.getenv("HR_EMAIL"), os.getenv("HR_PASSWORD")
    if hr_email and hr_pw and not db.query(User).filter(User.email == hr_email.lower()).first():
        create_user(db, email=hr_email, name=os.getenv("HR_NAME", "HR Admin"), password=hr_pw, role="hr")
    if settings.SEED_DEMO_ACCOUNTS:
        from .seed import DEMO_ACCOUNTS

        for acc in DEMO_ACCOUNTS:
            if db.query(User).filter(User.email == acc["email"]).first():
                continue
            cand = db.query(Candidate).filter(Candidate.email == acc.get("candidate_email")).first() if acc.get("candidate_email") else None
            create_user(db, email=acc["email"], name=acc["name"], password=acc["password"], role=acc["role"],
                        candidate_id=cand.id if cand else None)
            if cand:
                for app_ in cand.applications:
                    if app_.job.title in acc.get("applied_jobs", []):
                        app_.candidate_applied = True
                db.commit()


def refresh_stale_scores(db) -> None:
    """Re-score jobs whose stored results came from a different semantic engine."""
    from .models import Application, Job
    from .services.matcher import run_matching

    current = semantic.engine_name()
    stale_jobs = {jid for (jid,) in db.query(Application.job_id).filter(Application.engine != current).distinct()}
    for job in db.query(Job).filter(Job.id.in_(stale_jobs)):
        run_matching(db, job, [a.candidate for a in job.applications])
    if stale_jobs:
        logging.getLogger(__name__).info("Re-scored %d job(s) with engine %s", len(stale_jobs), current)


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    await asyncio.to_thread(semantic.load_model)  # load once so all scores use the same engine
    with SessionLocal() as db:
        if settings.SEED_DEMO:
            from .seed import seed_if_empty

            seed_if_empty(db)
        ensure_accounts(db)
        from .services.matcher import load_settings

        load_settings(db)  # HR Auto Shortlist on/off
        refresh_stale_scores(db)
    yield


app = FastAPI(
    title="MatchPoint",
    version="1.0.0",
    lifespan=lifespan,
    # interactive API docs are hidden in production (APP_ENV=production) unless ENABLE_DOCS=1
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
# Content-Security-Policy for the app's HTML pages. Styles allow 'unsafe-inline' because
# React/Recharts set inline style attributes; scripts are only loaded from this origin.
CSP = (
    "default-src 'self'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if request.url.scheme == "https":
        h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    # CSP only on HTML pages: resume PDFs open in the browser's built-in viewer
    if h.get("content-type", "").startswith("text/html"):
        h.setdefault("Content-Security-Policy", CSP)
    # API responses are per-user and must never be cached by the browser
    if request.url.path.startswith("/api/"):
        h["Cache-Control"] = "no-store"
    return response


app.include_router(auth.router)
app.include_router(portal.router)
app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok", "semantic_engine": semantic.engine_name()}


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_not_found(path: str):
    raise HTTPException(404, f"Unknown API endpoint: /api/{path}")


# Serve the built React app (npm run build) from the same server in production.
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = (FRONTEND_DIST / path).resolve()
        if path and target.is_file() and target.is_relative_to(FRONTEND_DIST.resolve()):
            return FileResponse(target)
        # index.html must be revalidated so a new build is picked up immediately
        return FileResponse(FRONTEND_DIST / "index.html", headers={"Cache-Control": "no-cache"})
