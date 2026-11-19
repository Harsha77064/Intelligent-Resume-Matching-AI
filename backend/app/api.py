"""REST API routes."""
from __future__ import annotations

import hashlib
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session, selectinload

from . import schemas
from .auth import require_hr
from .database import UPLOAD_DIR, get_db
from .models import Application, Candidate, Job
from .services import semantic
from .services.matcher import HIGH_THRESHOLD, MEDIUM_THRESHOLD, can_submit, route, run_matching
from .services.parser import ResumeParseError, parse_resume
from .services.skills import all_skills

router = APIRouter(prefix="/api", dependencies=[Depends(require_hr)])  # HR-only
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 50


# ================================================================== helpers
def _get(db: Session, model, id_: int):
    obj = db.get(model, id_)
    if not obj:
        raise HTTPException(404, f"{model.__name__} {id_} not found")
    return obj


def app_out(a: Application) -> schemas.ApplicationOut:
    c, j = a.candidate, a.job
    return schemas.ApplicationOut(
        id=a.id, job_id=a.job_id, job_title=j.title, candidate_id=a.candidate_id, candidate_name=c.name,
        candidate_email=c.email, experience_years=c.experience_years, score=a.score, match_band=a.match_band,
        breakdown=a.breakdown or {}, matched_skills=a.matched_skills or [], missing_skills=a.missing_skills or [],
        matched_preferred=a.matched_preferred or [], explanation=a.explanation, engine=a.engine, status=a.status,
        routing_reason=a.routing_reason, recruiter_notes=a.recruiter_notes, status_locked=a.status_locked,
        auto_apply=a.auto_apply, details_reviewed=a.details_reviewed, data_sharing_consent=a.data_sharing_consent,
        candidate_applied=a.candidate_applied, submitted_at=a.submitted_at, matched_at=a.matched_at, updated_at=a.updated_at,
    )


def cand_out(c: Candidate, detail: bool = False):
    apps = [
        schemas.AppBrief(id=a.id, job_id=a.job_id, job_title=a.job.title, score=a.score,
                         match_band=a.match_band, status=a.status)
        for a in sorted(c.applications, key=lambda a: -a.score)
    ]
    data = dict(
        id=c.id, name=c.name, email=c.email, phone=c.phone, resume_filename=c.resume_filename,
        skills=c.skills or [], education=c.education or [], experience_years=c.experience_years,
        corrected=c.corrected, auto_apply=c.auto_apply, details_reviewed=c.details_reviewed,
        data_sharing_consent=c.data_sharing_consent, created_at=c.created_at,
        best_score=apps[0].score if apps else None, applications=apps,
    )
    if detail:
        return schemas.CandidateDetail(**data, resume_text=c.resume_text)
    return schemas.CandidateOut(**data)


def _active_jobs(db: Session) -> list[Job]:
    return db.query(Job).filter(Job.status == "active").all()


def _rematch_candidate(db: Session, cand: Candidate) -> None:
    """Re-score a candidate against the jobs they are already being evaluated for."""
    job_ids = {a.job_id for a in cand.applications}
    for job in db.query(Job).filter(Job.id.in_(job_ids)):
        run_matching(db, job, [cand])


# ================================================================== meta
@router.get("/skills")
def skills():
    return all_skills()


@router.get("/config")
def config():
    return {
        "high_threshold": HIGH_THRESHOLD,
        "medium_threshold": MEDIUM_THRESHOLD,
        "semantic_engine": semantic.engine_name(),
        "weights": {"required_skills": 50, "preferred_skills": 10, "experience": 20, "semantic": 15, "education": 5},
        "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
    }


# ================================================================== dashboard
def _distribution(scores: list[float]) -> dict:
    high = sum(s >= HIGH_THRESHOLD for s in scores)
    med = sum(MEDIUM_THRESHOLD <= s < HIGH_THRESHOLD for s in scores)
    low = len(scores) - high - med
    return {"high": high, "medium": med, "low": low, "total": len(scores)}


def _pct_change(now: int, before: int) -> float | None:
    if before == 0:
        return None  # no baseline a week ago: a % change would be meaningless
    return round((now - before) / before * 100, 1)


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    total_jobs = db.query(func.count(Job.id)).scalar()
    jobs_before = db.query(func.count(Job.id)).filter(Job.created_at < week_ago).scalar()
    total_c = db.query(func.count(Candidate.id)).scalar()
    c_before = db.query(func.count(Candidate.id)).filter(Candidate.created_at < week_ago).scalar()
    analyzed = db.query(func.count(Candidate.id)).filter(Candidate.resume_text != "").scalar()
    analyzed_before = (
        db.query(func.count(Candidate.id))
        .filter(Candidate.resume_text != "", Candidate.created_at < week_ago).scalar()
    )
    # best score per candidate drives average + distribution (a candidate counts once)
    best = dict(db.query(Application.candidate_id, func.max(Application.score)).group_by(Application.candidate_id).all())
    scores = list(best.values())
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    status_counts = dict(db.query(Application.status, func.count(Application.id)).group_by(Application.status).all())
    return {
        "total_jobs": total_jobs, "jobs_change": _pct_change(total_jobs, jobs_before),
        "active_jobs": db.query(func.count(Job.id)).filter(Job.status == "active").scalar(),
        "total_candidates": total_c, "candidates_change": _pct_change(total_c, c_before),
        "resumes_analyzed": analyzed, "analyzed_change": _pct_change(analyzed, analyzed_before),
        "avg_match_score": avg,
        "distribution": _distribution(scores),
        "status_counts": status_counts,
        "semantic_engine": semantic.engine_name(),
    }


# ================================================================== jobs
def _job_out(job: Job, agg: dict) -> schemas.JobOut:
    out = schemas.JobOut.model_validate(job)
    n, avg, high = agg.get(job.id, (0, None, 0))
    out.candidates_matched, out.avg_score, out.high_matches = n, (round(avg, 1) if avg is not None else None), high or 0
    return out


def _job_aggs(db: Session) -> dict:
    rows = db.query(
        Application.job_id, func.count(Application.id), func.avg(Application.score),
        func.sum(case((Application.score >= HIGH_THRESHOLD, 1), else_=0)),
    ).group_by(Application.job_id).all()
    return {r[0]: (r[1], r[2], r[3]) for r in rows}


@router.get("/jobs", response_model=list[schemas.JobOut])
def list_jobs(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    aggs = _job_aggs(db)
    return [_job_out(j, aggs) for j in q.order_by(Job.created_at.desc())]


@router.post("/jobs", response_model=schemas.JobOut, status_code=201)
def create_job(body: schemas.JobIn, db: Session = Depends(get_db)):
    job = Job(**body.model_dump())
    db.add(job)
    db.commit()
    return _job_out(job, {})


@router.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return _job_out(_get(db, Job, job_id), _job_aggs(db))


@router.put("/jobs/{job_id}", response_model=schemas.JobOut)
def update_job(job_id: int, body: schemas.JobIn, db: Session = Depends(get_db)):
    job = _get(db, Job, job_id)
    criteria_before = (job.required_skills, job.preferred_skills, job.min_experience, job.education_level, job.description, job.title)
    for k, v in body.model_dump().items():
        setattr(job, k, v)
    db.commit()
    criteria_after = (job.required_skills, job.preferred_skills, job.min_experience, job.education_level, job.description, job.title)
    if criteria_before != criteria_after and job.applications:
        # keep existing results consistent with the edited requirements
        run_matching(db, job, [a.candidate for a in job.applications])
    return _job_out(job, _job_aggs(db))


@router.patch("/jobs/{job_id}/status", response_model=schemas.JobOut)
def set_job_status(job_id: int, status: schemas.JobStatus = Query(...), db: Session = Depends(get_db)):
    job = _get(db, Job, job_id)
    job.status = status
    db.commit()
    return _job_out(job, _job_aggs(db))


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, Job, job_id))
    db.commit()


# ================================================================== candidates
def _cand_query(db: Session):
    return db.query(Candidate).options(selectinload(Candidate.applications).selectinload(Application.job))


@router.get("/candidates", response_model=list[schemas.CandidateOut])
def list_candidates(search: str | None = None, db: Session = Depends(get_db)):
    q = _cand_query(db)
    rows = q.order_by(Candidate.created_at.desc()).all()
    if search:
        s = search.lower().strip()
        rows = [
            c for c in rows
            if s in c.name.lower() or s in (c.email or "").lower() or any(s in k.lower() for k in c.skills or [])
        ]
    return [cand_out(c) for c in rows]


@router.get("/candidates/{cid}", response_model=schemas.CandidateDetail)
def get_candidate(cid: int, db: Session = Depends(get_db)):
    c = _cand_query(db).filter(Candidate.id == cid).first()
    if not c:
        raise HTTPException(404, "Candidate not found")
    return cand_out(c, detail=True)


@router.get("/candidates/{cid}/resume")
def get_resume(cid: int, db: Session = Depends(get_db)):
    c = _get(db, Candidate, cid)
    if not c.resume_path or not (UPLOAD_DIR / c.resume_path).exists():
        raise HTTPException(404, "Resume file not available")
    return FileResponse(UPLOAD_DIR / c.resume_path, media_type="application/pdf",
                        filename=c.resume_filename or "resume.pdf", content_disposition_type="inline")


@router.post("/candidates/upload", response_model=schemas.UploadResult)
async def upload_resumes(
    files: list[UploadFile] = File(...),
    job_id: int | None = Form(None),
    name: str | None = Form(None),
    email: str | None = Form(None),
    phone: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """HR upload of one or many PDF resumes. Applicant details apply when a single file is sent.

    Consent / Auto Apply can only be given by the candidate in the candidate portal, so
    HR-uploaded resumes never auto-submit.
    """
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(400, f"At most {MAX_FILES_PER_UPLOAD} files per upload")
    job = _get(db, Job, job_id) if job_id else None
    if job and job.status != "active":
        raise HTTPException(400, "Job is not active")
    single = len(files) == 1
    created: list[Candidate] = []
    errors: list[dict] = []
    for f in files:
        fname = f.filename or "resume.pdf"
        data = await f.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            errors.append({"file": fname, "error": "File larger than 10 MB"})
            continue
        if not fname.lower().endswith(".pdf"):
            errors.append({"file": fname, "error": "Only PDF files are supported"})
            continue
        digest = hashlib.sha256(data).hexdigest()
        dup = db.query(Candidate).filter(Candidate.resume_hash == digest).first()
        if dup:
            errors.append({"file": fname, "error": f"Duplicate of existing resume ({dup.name})"})
            continue
        try:
            parsed = parse_resume(data)
        except ResumeParseError as exc:
            errors.append({"file": fname, "error": str(exc)})
            continue
        stored = f"{uuid.uuid4().hex}.pdf"
        (UPLOAD_DIR / stored).write_bytes(data)
        cand = Candidate(
            name=(name if single and name else parsed.name) or fname.rsplit(".", 1)[0].replace("_", " ").title(),
            email=(email if single and email else parsed.email),
            phone=(phone if single and phone else parsed.phone),
            resume_filename=fname, resume_path=stored, resume_hash=digest, resume_text=parsed.text,
            skills=parsed.skills, education=parsed.education, experience_years=parsed.experience_years,
            parse_ms=parsed.parse_ms,
        )
        db.add(cand)
        created.append(cand)
    db.commit()
    if created:
        targets = [job] if job else _active_jobs(db)
        for j in targets:
            run_matching(db, j, created)
    for c in created:
        db.refresh(c)
    return schemas.UploadResult(
        created=[cand_out(c) for c in created], errors=errors, matched_job_id=job.id if job else None
    )


@router.patch("/candidates/{cid}", response_model=schemas.CandidateDetail)
def update_candidate(cid: int, body: schemas.CandidateUpdate, db: Session = Depends(get_db)):
    c = _get(db, Candidate, cid)
    changes = body.model_dump(exclude_unset=True)
    parsed_fields = {"skills", "education", "experience_years"}
    for k, v in changes.items():
        setattr(c, k, v)
    if parsed_fields & changes.keys():
        c.corrected = True
    db.commit()
    # Corrections or consent changes can alter score/routing: re-evaluate.
    if changes.keys() & parsed_fields:
        _rematch_candidate(db, c)
    return get_candidate(cid, db)


@router.delete("/candidates/{cid}", status_code=204)
def delete_candidate(cid: int, db: Session = Depends(get_db)):
    c = _get(db, Candidate, cid)
    if c.resume_path:
        (UPLOAD_DIR / c.resume_path).unlink(missing_ok=True)
    db.delete(c)
    db.commit()


# ================================================================== matching
def _app_query(db: Session):
    return db.query(Application).options(selectinload(Application.candidate), selectinload(Application.job))


@router.post("/match/{job_id}", response_model=schemas.MatchRunOut)
def run_match(job_id: int, db: Session = Depends(get_db)):
    job = _get(db, Job, job_id)
    t0 = time.perf_counter()
    cands = db.query(Candidate).filter(Candidate.resume_text != "").all()
    apps = run_matching(db, job, cands)
    apps.sort(key=lambda a: -a.score)
    return schemas.MatchRunOut(
        job_id=job.id, processed=len(apps), engine=apps[0].engine if apps else semantic.engine_name(),
        duration_ms=round((time.perf_counter() - t0) * 1000, 1), results=[app_out(a) for a in apps],
    )


@router.get("/match/{job_id}", response_model=list[schemas.ApplicationOut])
def match_results(
    job_id: int, search: str | None = None, band: str | None = None, min_score: float = 0,
    db: Session = Depends(get_db),
):
    _get(db, Job, job_id)
    q = _app_query(db).filter(Application.job_id == job_id, Application.score >= min_score)
    if band:
        q = q.filter(Application.match_band == band)
    apps = q.order_by(Application.score.desc()).all()
    if search:
        s = search.lower().strip()
        apps = [
            a for a in apps
            if s in a.candidate.name.lower() or s in (a.candidate.email or "").lower()
            or any(s in k.lower() for k in a.candidate.skills or [])
        ]
    return [app_out(a) for a in apps]


# ================================================================== applications
@router.get("/applications", response_model=list[schemas.ApplicationOut])
def list_applications(status: str | None = None, job_id: int | None = None, candidate_id: int | None = None,
                      db: Session = Depends(get_db)):
    q = _app_query(db)
    if status:
        q = q.filter(Application.status == status)
    if job_id:
        q = q.filter(Application.job_id == job_id)
    if candidate_id:
        q = q.filter(Application.candidate_id == candidate_id)
    return [app_out(a) for a in q.order_by(Application.score.desc())]


@router.get("/applications/{app_id}", response_model=schemas.ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    a = _app_query(db).filter(Application.id == app_id).first()
    if not a:
        raise HTTPException(404, "Application not found")
    return app_out(a)


@router.patch("/applications/{app_id}", response_model=schemas.ApplicationOut)
def update_application(app_id: int, body: schemas.ApplicationUpdate, db: Session = Depends(get_db)):
    a = _get(db, Application, app_id)
    if body.recruiter_notes is not None:
        a.recruiter_notes = body.recruiter_notes
    if body.reset_to_auto:
        a.status_locked = False
        route(a)
    elif body.status:
        if body.status == "submitted" and not can_submit(a):
            raise HTTPException(
                400, "Cannot submit: the candidate has not applied to this job with Auto Apply, "
                     "reviewed details and consent to data sharing."
            )
        a.status = body.status
        a.status_locked = body.status in {"shortlisted", "rejected"}
        a.routing_reason = (
            f"Recruiter decision: {body.status.replace('_', ' ')}." if a.status_locked else a.routing_reason
        )
    db.commit()
    return get_application(app_id, db)


# ================================================================== reports
@router.get("/reports")
def reports(db: Session = Depends(get_db)):
    apps = _app_query(db).all()
    buckets = Counter(min(int(a.score // 10), 9) for a in apps)
    histogram = [{"range": f"{i * 10}-{i * 10 + 9 if i < 9 else 100}", "count": buckets.get(i, 0)} for i in range(10)]

    by_job: dict[int, dict] = defaultdict(lambda: Counter())
    titles: dict[int, str] = {}
    scores_by_job: dict[int, list[float]] = defaultdict(list)
    for a in apps:
        by_job[a.job_id][a.status] += 1
        titles[a.job_id] = a.job.title
        scores_by_job[a.job_id].append(a.score)
    for j in db.query(Job):
        titles.setdefault(j.id, j.title)
    applications_by_job = [
        {"job_id": jid, "job": titles[jid], "total": sum(by_job[jid].values()),
         "avg_score": round(sum(scores_by_job[jid]) / len(scores_by_job[jid]), 1) if scores_by_job[jid] else 0,
         **{s: by_job[jid].get(s, 0) for s in
            ["submitted", "pending_consent", "recruiter_review", "standard_review", "shortlisted", "rejected"]}}
        for jid in titles
    ]

    skill_gaps = Counter(s for a in apps for s in (a.missing_skills or []))
    cands = db.query(Candidate.parse_ms, Candidate.created_at, Candidate.corrected).all()
    parse_times = [c.parse_ms for c in cands if c.parse_ms]
    match_times = [a.match_ms for a in apps if a.match_ms]
    per_day = Counter(c.created_at.date().isoformat() for c in cands)
    return {
        "score_histogram": histogram,
        "applications_by_job": applications_by_job,
        "status_counts": dict(Counter(a.status for a in apps)),
        "top_missing_skills": [{"skill": s, "count": n} for s, n in skill_gaps.most_common(8)],
        "processing": {
            "resumes_processed": len(cands),
            "avg_parse_ms": round(sum(parse_times) / len(parse_times), 1) if parse_times else 0,
            "avg_match_ms": round(sum(match_times) / len(match_times), 2) if match_times else 0,
            "evaluations": len(apps),
            "corrected_profiles": sum(1 for c in cands if c.corrected),
            "semantic_engine": semantic.engine_name(),
            "uploads_per_day": [{"date": d, "count": n} for d, n in sorted(per_day.items())[-14:]],
        },
    }
