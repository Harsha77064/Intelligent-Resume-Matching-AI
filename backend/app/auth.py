"""Authentication: password hashing, signed session cookies and role guards.

Two roles:
  hr        - recruiter dashboard (all /api routes except /api/auth and /api/portal)
  candidate - candidate portal (/api/portal only: jobs, own resume, own scores)

HR accounts cannot self-register; they are created with:
    python -m app.users create-hr --email you@company.com --name "Your Name"
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from . import settings
from .database import DATA_DIR, get_db
from .mailer import send_email
from .models import PasswordReset, User

# One cookie per role, so the same browser can be signed in as HR and as a candidate
# at the same time (e.g. HR dashboard in one tab, candidate portal in another).
COOKIES = {"hr": "mp_hr", "candidate": "mp_candidate"}
LEGACY_COOKIE = "mp_session"
SESSION_SECONDS = 7 * 24 * 3600
PBKDF2_ROUNDS = 240_000


def _secret() -> bytes:
    env = os.getenv("SECRET_KEY")
    if env:
        return env.encode()
    path = DATA_DIR / "secret.key"
    if not path.exists():
        path.write_text(secrets.token_hex(32))
    return path.read_text().strip().encode()


SECRET = _secret()


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split("$")
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(check.hex(), digest)
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------ tokens
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _pw_version(user: User) -> str:
    """Short fingerprint of the password hash. Changing the password invalidates old sessions."""
    return hmac.new(SECRET, user.password_hash.encode(), hashlib.sha256).hexdigest()[:16]


def make_token(user: User) -> str:
    payload = _b64(json.dumps({"uid": user.id, "role": user.role, "pv": _pw_version(user),
                               "exp": int(time.time()) + SESSION_SECONDS}).encode())
    sig = _b64(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(token: str) -> dict | None:
    try:
        payload, sig = token.split(".")
        expected = _b64(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return data if data.get("exp", 0) > time.time() else None
    except (ValueError, json.JSONDecodeError):
        return None


# ------------------------------------------------------------------ guards
def session_user(request: Request, db: Session, role: str) -> User | None:
    """The user signed in for `role` in this browser, or None."""
    data = read_token(request.cookies.get(COOKIES[role], ""))
    if not data or data.get("role") != role:
        return None
    user = db.get(User, data["uid"])
    if not user or user.role != role or not hmac.compare_digest(str(data.get("pv", "")), _pw_version(user)):
        return None
    return user


def _require(role: str, other: str, message: str):
    def dep(request: Request, db: Session = Depends(get_db)) -> User:
        user = session_user(request, db, role)
        if user:
            return user
        if session_user(request, db, other):
            raise HTTPException(403, message)  # signed in, but only with the other role
        raise HTTPException(401, "Please sign in.")
    return dep


require_hr = _require("hr", "candidate", "This area is for HR staff only.")
require_candidate = _require("candidate", "hr", "This area is for candidates only.")


# ------------------------------------------------------------------ rate limit
_FAILS: dict[str, deque] = defaultdict(deque)
MAX_FAILS, WINDOW = 8, 15 * 60


MAX_TRACKED_KEYS = 10_000


def _recent(store: dict[str, deque], key: str, window: float) -> deque:
    """The timestamps for `key` inside `window`, dropping older ones.

    Keys whose timestamps have all expired are removed when the store gets large, so the
    in-memory limiters cannot grow without bound on a busy or attacked server.
    """
    cutoff = time.time() - window
    if len(store) > MAX_TRACKED_KEYS:
        for k in [k for k, q in store.items() if not q or q[-1] < cutoff]:
            del store[k]
    q = store[key]
    while q and q[0] < cutoff:
        q.popleft()
    return q


def _too_many(key: str) -> bool:
    return len(_recent(_FAILS, key, WINDOW)) >= MAX_FAILS


# ------------------------------------------------------------------ routes
router = APIRouter(prefix="/api/auth")


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)  # lookup only; format is validated at registration
    password: str = Field(min_length=1, max_length=200)
    # Which portal's login page is being used. An account of the other role is rejected
    # with the same message as a wrong password, so neither page reveals the other's accounts.
    role: Literal["hr", "candidate"] = "candidate"


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}


def _set_cookie(resp: Response, user: User, request: Request) -> None:
    resp.set_cookie(
        COOKIES[user.role], make_token(user), max_age=SESSION_SECONDS, httponly=True, samesite="lax",
        secure=settings.COOKIE_SECURE if settings.COOKIE_SECURE is not None else request.url.scheme == "https",
        path="/",
    )
    resp.delete_cookie(LEGACY_COOKIE, path="/")


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    key = f"{request.client.host if request.client else '-'}:{body.email.lower()}"
    if _too_many(key):
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or user.role != body.role or not verify_password(body.password, user.password_hash):
        _FAILS[key].append(time.time())
        raise HTTPException(401, "Incorrect email or password.")
    _FAILS.pop(key, None)
    _set_cookie(response, user, request)
    return user_out(user)


@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    """Candidate self-registration. HR accounts can only be created from the command line."""
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists.")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password), role="candidate")
    db.add(user)
    db.commit()
    _set_cookie(response, user, request)
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response, role: str | None = None):
    """Sign out of one role (?role=hr|candidate), or of both when no role is given."""
    if role is not None and role not in COOKIES:
        raise HTTPException(400, "role must be 'hr' or 'candidate'")
    for r in [role] if role else list(COOKIES):
        response.delete_cookie(COOKIES[r], path="/")
    response.delete_cookie(LEGACY_COOKIE, path="/")


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    """Both sessions this browser holds: {"hr": user|null, "candidate": user|null}."""
    out = {}
    for role in COOKIES:
        u = session_user(request, db, role)
        out[role] = user_out(u) if u else None
    return out


class ChangePasswordIn(BaseModel):
    role: Literal["hr", "candidate"]
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


@router.post("/change-password")
def change_password(body: ChangePasswordIn, request: Request, response: Response, db: Session = Depends(get_db)):
    """Change the password of the account signed in for `role`. Other devices are signed out."""
    user = session_user(request, db, body.role)
    if not user:
        raise HTTPException(401, "Please sign in.")
    key = f"change:{user.id}"
    if _too_many(key):
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    if not verify_password(body.current_password, user.password_hash):
        _FAILS[key].append(time.time())
        raise HTTPException(400, "Your current password is incorrect.")
    if body.new_password == body.current_password:
        raise HTTPException(400, "Choose a password different from your current one.")
    user.password_hash = hash_password(body.new_password)  # invalidates every existing session
    db.commit()
    _FAILS.pop(key, None)
    _set_cookie(response, user, request)  # keep this browser signed in
    return {"message": "Password changed. You've been signed out on your other devices."}


# ------------------------------------------------------------------ password reset
RESET_MINUTES = 10
RESET_MAX_ATTEMPTS = 5
RESEND_SECONDS = 60
MAX_REQUESTS, REQUEST_WINDOW = 5, 60 * 60  # per email, from any IP address
MAX_IP_REQUESTS = 20  # per IP address, for any emails
_REQUESTS: dict[str, deque] = defaultdict(deque)
RESET_SENT = "If an account exists for this email, we've sent a 6-digit code to it. It expires in 10 minutes."
BAD_CODE = "This code is incorrect or has expired. Request a new one."


class ForgotIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    role: Literal["hr", "candidate"] = "candidate"


class ResetIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    role: Literal["hr", "candidate"] = "candidate"
    code: str = Field(pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=200)


def _code_hash(user_id: int, code: str) -> str:
    return hmac.new(SECRET, f"reset:{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _reset_email(user: User, code: str) -> tuple[str, str, str]:
    portal = "HR dashboard" if user.role == "hr" else "candidate portal"
    subject = f"Your MatchPoint password reset code: {code}"
    text = (f"Hi {user.name},\n\nUse this code to reset your MatchPoint {portal} password:\n\n    {code}\n\n"
            f"It expires in {RESET_MINUTES} minutes. If you didn't ask to reset your password, ignore this email; "
            "your password stays the same.\n\n- MatchPoint")
    html = (f'<div style="font-family:Arial,sans-serif;max-width:480px;color:#0f172a">'
            f"<p>Hi {_esc(user.name)},</p><p>Use this code to reset your MatchPoint {portal} password:</p>"
            f'<p style="font-size:30px;font-weight:700;letter-spacing:8px;background:#f1f5f9;padding:14px 18px;'
            f'border-radius:10px;text-align:center">{code}</p>'
            f'<p>It expires in {RESET_MINUTES} minutes.</p><p style="color:#64748b;font-size:13px">'
            "If you didn't ask to reset your password, ignore this email; your password stays the same.</p></div>")
    return subject, text, html


@router.post("/forgot-password")
def forgot_password(body: ForgotIn, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Email a 6-digit code. Always answers the same way, so it never reveals which emails have accounts."""
    email = body.email.strip().lower()
    # Limits are per email (whatever the IP) so many IPs can't flood one inbox or keep
    # refreshing codes to guess, plus per IP so one client can't spray many emails.
    by_email = _recent(_REQUESTS, f"email:{email}", REQUEST_WINDOW)
    by_ip = _recent(_REQUESTS, f"ip:{request.client.host if request.client else '-'}", REQUEST_WINDOW)
    if len(by_email) >= MAX_REQUESTS or len(by_ip) >= MAX_IP_REQUESTS:
        raise HTTPException(429, "Too many code requests. Try again in an hour.")
    if by_email and by_email[-1] > time.time() - RESEND_SECONDS:
        raise HTTPException(429, f"Please wait {RESEND_SECONDS} seconds before requesting another code.")
    now_ts = time.time()
    by_email.append(now_ts)
    by_ip.append(now_ts)

    user = db.query(User).filter(User.email == email).first()
    if user and user.role == body.role:  # each portal only resets its own accounts
        code = f"{secrets.randbelow(1_000_000):06d}"
        now = datetime.now(timezone.utc)
        row = db.get(PasswordReset, user.id) or PasswordReset(user_id=user.id)
        row.code_hash = _code_hash(user.id, code)
        row.expires_at = now + timedelta(minutes=RESET_MINUTES)
        row.attempts = 0
        row.created_at = now
        db.add(row)
        db.commit()
        tasks.add_task(send_email, user.email, *_reset_email(user, code))
    return {"message": RESET_SENT}


@router.post("/reset-password")
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    row = db.get(PasswordReset, user.id) if user and user.role == body.role else None
    if not row:
        raise HTTPException(400, BAD_CODE)
    if _aware(row.expires_at) < datetime.now(timezone.utc) or row.attempts >= RESET_MAX_ATTEMPTS:
        db.delete(row)
        db.commit()
        raise HTTPException(400, BAD_CODE)
    if not hmac.compare_digest(row.code_hash, _code_hash(user.id, body.code)):
        row.attempts += 1
        left = RESET_MAX_ATTEMPTS - row.attempts
        if left <= 0:
            db.delete(row)
        db.commit()
        if left <= 0:
            raise HTTPException(400, BAD_CODE)
        raise HTTPException(400, f"This code is incorrect. {left} attempt{'s' if left != 1 else ''} left.")
    user.password_hash = hash_password(body.password)  # new fingerprint: signs out every existing session
    db.delete(row)
    db.commit()
    for k in [k for k in _FAILS if k.endswith(f":{email}")]:
        _FAILS.pop(k, None)  # clear any login lockout for this account
    return {"message": "Your password has been changed. Sign in with your new password."}


def create_user(db: Session, *, email: str, name: str, password: str, role: str, candidate_id: int | None = None) -> User:
    user = User(email=email.lower(), name=name, password_hash=hash_password(password), role=role, candidate_id=candidate_id)
    db.add(user)
    db.commit()
    return user
