"""Runtime settings from environment variables (or backend/.env).

APP_ENV=production turns on safe defaults for a public deployment:
  * session cookies are always marked Secure (HTTPS only)
  * the interactive API docs (/docs, /redoc, /openapi.json) are hidden
  * demo data and demo accounts are off unless SEED_DEMO=1 is set explicitly
"""
import os


def _flag(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"

# "auto" = Secure only when the request arrived over HTTPS (works locally over http).
_cookie = os.getenv("COOKIE_SECURE", "true" if IS_PRODUCTION else "auto").strip().lower()
COOKIE_SECURE: bool | None = None if _cookie == "auto" else _cookie in {"1", "true", "yes", "on"}

ENABLE_DOCS = _flag("ENABLE_DOCS", not IS_PRODUCTION)
SEED_DEMO = _flag("SEED_DEMO", not IS_PRODUCTION)

# Outgoing email (password-reset codes). Without SMTP_HOST, codes are printed to the
# server log in development and not sent at all in production.
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "").strip() or SMTP_USERNAME
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "starttls").strip().lower()  # starttls | ssl | none
EMAIL_CONFIGURED = bool(SMTP_HOST and SMTP_FROM)
