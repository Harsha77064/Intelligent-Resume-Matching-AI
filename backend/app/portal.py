"""Candidate portal API: browse open jobs, upload own resume, apply, see own score + AI explanation.

Every route requires a signed-in *candidate* and only ever reads/writes that
candidate's own profile. Recruiter-only data (queues, notes, other candidates)
is never exposed here.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import COOKIES, require_candidate, verify_password
from .database import UPLOAD_DIR, get_db
from .models import Application, Candidate, Job, User
from .services.matcher import route, run_matching
from .services.parser import ResumeParseError, parse_resume

router = APIRouter(prefix="/api/portal")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _my_candidate(db: Session, user: User) -> Candidate | None:
    return db.get(Candidate, user.candidate_id) if user.candidate_id else None


def _profile(c: Candidate | None) -> dict:
    if not c or not c.resume_text:
        return {"has_resume": False}
    return {
        "has_resume": True,
        "resume_filename": c.resume_filename,
        "uploaded_at": c.updated_at,
        "skills": c.skills or [],
        "experience_years": c.experience_years,
        "education": c.education or [],
    }


def _for_candidate(text: str) -> str:
    """Rephrase the recruiter-facing explanation in the second person."""
    return (
        text.replace("The candidate shows", "Your resume shows")
        .replace("were found in the resume", "were found in your resume")
        .replace("Overall resume content shows", "Overall, your resume shows")
        .replace("not found in the resume and can be verified during the interview",
                 "not found in your resume. If you have them, add them to your resume")
    )


def _result(a: Application) -> dict:
    return {
        "job_id": a.job_id,
        "job_title": a.job.title,
        "company": a.job.company,
        "score": a.score,
        "match_band": a.match_band,
        "explanation": _for_candidate(a.explanation),
        "matched_skills": a.matched_skills or [],
        "missing_skills": a.missing_skills or [],
        "matched_preferred": a.matched_preferred or [],
        "breakdown": a.breakdown or {},
        "applied_at": a.matched_at,
    }


@router.get("/me")
def me(user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    return {"name": user.name, "email": user.email, **_profile(_my_candidate(db, user))}


@router.get("/jobs")
def jobs(user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    cand = _my_candidate(db, user)
    applied = {a.job_id: a.score for a in cand.applications if a.candidate_applied} if cand else {}
    rows = db.query(Job).filter(Job.status == "active").order_by(Job.created_at.desc()).all()
    return [
        {
            "id": j.id, "title": j.title, "company": j.company, "department": j.department,
            "location": j.location, "employment_type": j.employment_type, "description": j.description,
            "required_skills": j.required_skills, "preferred_skills": j.preferred_skills,
            "min_experience": j.min_experience, "education_level": j.education_level,
            "applied": j.id in applied, "score": applied.get(j.id),
        }
        for j in rows
    ]


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...), user: User = Depends(require_candidate), db: Session = Depends(get_db)
):
    """Upload or replace the candidate's own resume. Existing applications are re-scored."""
    fname = file.filename or "resume.pdf"
    if not fname.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "File is larger than 10 MB.")
    try:
        parsed = parse_resume(data)
    except ResumeParseError as exc:
        raise HTTPException(400, str(exc)) from exc

    digest = hashlib.sha256(data).hexdigest()
    stored = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / stored).write_bytes(data)
    cand = _my_candidate(db, user)
    if cand is None:
        # HR may already have uploaded this exact PDF. Holding the identical file shows it's the
        # same person, so take over that profile (keeping HR's screening history) instead of
        # creating a duplicate. Profiles already linked to another account are never taken.
        linked = {cid for (cid,) in db.query(User.candidate_id).filter(User.candidate_id.isnot(None))}
        cand = next((c for c in db.query(Candidate).filter(Candidate.resume_hash == digest) if c.id not in linked), None)
        if cand is None:
            cand = Candidate(name=user.name, email=user.email)
            db.add(cand)
        else:
            cand.name, cand.email = user.name, user.email
    if cand.resume_path:  # replace the previous copy of the file
        (UPLOAD_DIR / cand.resume_path).unlink(missing_ok=True)
    cand.phone = parsed.phone or cand.phone
    cand.resume_filename = fname
    cand.resume_path = stored
    cand.resume_hash = digest
    cand.resume_text = parsed.text
    cand.skills = parsed.skills
    cand.education = parsed.education
    cand.experience_years = parsed.experience_years
    cand.parse_ms = parsed.parse_ms
    cand.corrected = False
    cand.updated_at = datetime.now().astimezone()
    db.commit()
    if user.candidate_id != cand.id:
        user.candidate_id = cand.id
        db.commit()
    for app in list(cand.applications):
        run_matching(db, app.job, [cand])
    return _profile(cand)


class ApplyIn(BaseModel):
    details_reviewed: bool
    data_sharing_consent: bool
    auto_apply: bool = False


@router.post("/apply/{job_id}")
def apply(job_id: int, body: ApplyIn, user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or job.status != "active":
        raise HTTPException(404, "This job is not open for applications.")
    cand = _my_candidate(db, user)
    if not cand or not cand.resume_text:
        raise HTTPException(400, "Upload your resume before applying.")
    if not (body.details_reviewed and body.data_sharing_consent):
        raise HTTPException(400, "Please confirm you reviewed your details and consent to share your resume.")
    # profile keeps the candidate's latest choices (shown to HR); the application holds the consent for THIS job
    cand.details_reviewed = True
    cand.data_sharing_consent = True
    cand.auto_apply = body.auto_apply
    db.commit()
    app = run_matching(db, job, [cand])[0]
    app.candidate_applied = True
    app.details_reviewed = True
    app.data_sharing_consent = True
    app.auto_apply = body.auto_apply
    route(app)
    db.commit()
    return _result(app)


@router.get("/results")
def results(user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    cand = _my_candidate(db, user)
    if not cand:
        return []
    mine = [a for a in cand.applications if a.candidate_applied]
    return [_result(a) for a in sorted(mine, key=lambda a: a.matched_at, reverse=True)]


class DeleteAccountIn(BaseModel):
    password: str


@router.post("/delete-account", status_code=204)
def delete_account(body: DeleteAccountIn, response: Response, user: User = Depends(require_candidate),
                   db: Session = Depends(get_db)):
    """Permanently delete the candidate's account, resume file, profile and all their match results."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(400, "Your password is incorrect.")
    cand = _my_candidate(db, user)
    if cand:
        if cand.resume_path:
            (UPLOAD_DIR / cand.resume_path).unlink(missing_ok=True)
        db.delete(cand)  # applications are deleted with it
    db.delete(user)
    db.commit()
    response.delete_cookie(COOKIES["candidate"], path="/")
