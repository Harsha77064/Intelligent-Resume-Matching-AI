"""Explainable job-resume matching and application routing.

Score (0-100) is a weighted sum of job-related components only:
  required skills 50 | preferred skills 10 | experience 20 | semantic fit 15 | education 5
Weights are re-distributed when a job has no preferred skills / no education
requirement, so a score always reflects what the job actually asks for.

Routing rules (from the project brief):
  >= 80  high match  -> auto-submit ONLY if candidate enabled Auto Apply, reviewed
                        details and consented to data sharing; if Auto Apply is on
                        but a consent step is missing -> pending_consent; otherwise
                        recruiter_review.
  60-79  medium      -> recruiter_review
  < 60   low         -> standard_review
The score is advisory; recruiters make the final decision (shortlist / reject).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..models import Application, Candidate, Job, Setting
from ..models import utcnow
from .parser import LEVEL_NAMES, education_level
from .semantic import similarity_batch
from .skills import normalize_skill, text_has_skill

HIGH_THRESHOLD = 80
MEDIUM_THRESHOLD = 60
BASE_WEIGHTS = {"required_skills": 50, "preferred_skills": 10, "experience": 20, "semantic": 15, "education": 5}
LOCKED_STATUSES = {"shortlisted", "rejected"}


@dataclass
class MatchResult:
    score: float
    band: str
    breakdown: dict
    matched: list[str]
    missing: list[str]
    matched_preferred: list[str]
    missing_preferred: list[str] = field(default_factory=list)
    explanation: str = ""


def band_for(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def job_text(job: Job) -> str:
    parts = [job.title, job.description, "Skills: " + ", ".join(job.required_skills + job.preferred_skills)]
    return "\n".join(p for p in parts if p)


def _has(candidate_skills: set[str], resume_text: str, skill: str) -> bool:
    canon = normalize_skill(skill)
    if canon.lower() in candidate_skills:
        return True
    # Custom (non-dictionary) job skills are searched in the raw resume text.
    from .skills import is_known

    return not is_known(canon) and text_has_skill(resume_text, canon)


def _weights(job: Job) -> dict[str, float]:
    w = dict(BASE_WEIGHTS)
    if not job.preferred_skills:
        w["required_skills"] += w.pop("preferred_skills")
    if not job.education_level:
        w["required_skills"] += w.pop("education")
    if not job.required_skills:
        w["semantic"] += w.pop("required_skills")
    return w


def score_candidate(job: Job, cand: Candidate, semantic: float) -> MatchResult:
    cskills = {s.lower() for s in (cand.skills or [])}
    text = cand.resume_text or ""

    req = job.required_skills or []
    pref = job.preferred_skills or []
    matched = [s for s in req if _has(cskills, text, s)]
    missing = [s for s in req if s not in matched]
    matched_pref = [s for s in pref if _has(cskills, text, s)]
    missing_pref = [s for s in pref if s not in matched_pref]

    comps: dict[str, float] = {
        "required_skills": len(matched) / len(req) if req else 1.0,
        "preferred_skills": len(matched_pref) / len(pref) if pref else 1.0,
        "experience": min(1.0, (cand.experience_years or 0) / job.min_experience) if job.min_experience else 1.0,
        "semantic": semantic,
    }
    cand_level = education_level(cand.education or [])
    if job.education_level:
        comps["education"] = 1.0 if cand_level >= job.education_level else (0.5 if cand_level else 0.0)
    else:
        comps["education"] = 1.0

    weights = _weights(job)
    score = round(sum(weights[k] * comps[k] for k in weights), 1)
    breakdown = {
        k: {"weight": weights[k], "value": round(comps[k], 3), "points": round(weights[k] * comps[k], 1)}
        for k in weights
    }
    res = MatchResult(
        score=score,
        band=band_for(score),
        breakdown=breakdown,
        matched=matched,
        missing=missing,
        matched_preferred=matched_pref,
        missing_preferred=missing_pref,
    )
    res.explanation = explain(job, cand, res, cand_level)
    return res


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def explain(job: Job, cand: Candidate, r: MatchResult, cand_level: int) -> str:
    req = job.required_skills or []
    parts: list[str] = []
    if req:
        if r.matched:
            parts.append(
                f"The candidate shows {len(r.matched)} of {len(req)} required skills ({_join(r.matched)})."
            )
        else:
            parts.append(f"None of the {len(req)} required skills were found in the resume.")
    if r.matched_preferred:
        parts.append(f"Bonus skills present: {_join(r.matched_preferred)}.")
    exp = cand.experience_years or 0
    if job.min_experience:
        if exp >= job.min_experience:
            parts.append(f"{exp:g} years of experience meets the {job.min_experience:g}-year requirement.")
        else:
            parts.append(f"{exp:g} years of experience is below the {job.min_experience:g}-year requirement.")
    if job.education_level:
        need = LEVEL_NAMES.get(job.education_level, "")
        have = LEVEL_NAMES.get(cand_level, "no degree detected") if cand_level else "no degree detected"
        ok = "meets" if cand_level >= job.education_level else "does not meet"
        parts.append(f"Education ({have}) {ok} the {need} requirement.")
    sem = r.breakdown["semantic"]["value"]
    fit = "strong" if sem >= 0.7 else "moderate" if sem >= 0.4 else "limited"
    parts.append(f"Overall resume content shows {fit} alignment with the job description.")
    if r.missing:
        parts.append(
            f"{_join(r.missing)} {'was' if len(r.missing) == 1 else 'were'} not found in the resume "
            "and can be verified during the interview."
        )
    return " ".join(parts)


def can_submit(app: Application) -> bool:
    """Only an application the candidate made themselves, for THIS job, with full consent."""
    return bool(app.candidate_applied and app.auto_apply and app.details_reviewed and app.data_sharing_consent)


# HR "Auto Shortlist": while on, every application scoring 80%+ for its job is shortlisted
# without HR intervention. Mirrored from the settings table at startup and when HR changes it.
AUTO_SHORTLIST = {"on": False}


def route(app: Application) -> None:
    """Apply the routing rules, then HR Auto Shortlist. Recruiter decisions (locked) are never changed."""
    if app.status_locked:
        return
    _route_by_score_and_consent(app)
    job = app.job
    if AUTO_SHORTLIST["on"] and app.score >= HIGH_THRESHOLD and (job is None or job.status == "active"):
        app.status = "shortlisted"
        app.routing_reason = (
            f"Auto-shortlisted: high match ({int(app.score + 0.5)}%) for this job and HR Auto Shortlist is on. "
            + app.routing_reason
        )


def _route_by_score_and_consent(app: Application) -> None:
    """Apply the auto-apply / review routing rules to an application.

    Consent is per application: a candidate who agreed to Auto Apply for one job is never
    auto-submitted to another job that HR screened them for.
    """
    s = app.score
    if s >= HIGH_THRESHOLD:
        if not app.candidate_applied:
            app.submitted_at = None
            app.status = "recruiter_review"
            app.routing_reason = (
                f"High match ({int(s + 0.5)}%) found by HR screening. The candidate has not applied to this job, "
                "so it was placed in the recruiter review queue."
            )
            return
        if can_submit(app):
            app.status = "submitted"
            app.routing_reason = (
                f"High match ({int(s + 0.5)}%). Candidate enabled Auto Apply, reviewed details and consented "
                "to data sharing, so the application was submitted (simulated ATS submission)."
            )
            app.submitted_at = app.submitted_at or utcnow()
            return
        app.submitted_at = None
        if app.auto_apply:
            missing = []
            if not app.details_reviewed:
                missing.append("review of application details")
            if not app.data_sharing_consent:
                missing.append("consent to share resume/personal data")
            app.status = "pending_consent"
            app.routing_reason = (
                f"High match ({int(s + 0.5)}%) with Auto Apply on, but awaiting {_join(missing)}. "
                "Not submitted until the candidate completes these steps."
            )
        else:
            app.status = "recruiter_review"
            app.routing_reason = f"High match ({int(s + 0.5)}%). Auto Apply is off, so placed in the recruiter review queue."
    elif s >= MEDIUM_THRESHOLD:
        app.submitted_at = None
        app.status = "recruiter_review"
        app.routing_reason = f"Medium match ({int(s + 0.5)}%, 60-79%). Sent to recruiter review."
    else:
        app.submitted_at = None
        app.status = "standard_review"
        app.routing_reason = f"Match below 60% ({int(s + 0.5)}%). Kept in the standard review queue."


def run_matching(db, job: Job, candidates: list[Candidate]) -> list[Application]:
    """Score candidates against a job (batched semantic step) and upsert applications."""
    if not candidates:
        return []
    t0 = time.perf_counter()
    sims, engine = similarity_batch(job_text(job), [c.resume_text or "" for c in candidates])
    existing = {
        a.candidate_id: a
        for a in db.query(Application).filter(
            Application.job_id == job.id, Application.candidate_id.in_([c.id for c in candidates])
        )
    }
    per_ms = (time.perf_counter() - t0) * 1000 / len(candidates)
    out: list[Application] = []
    for cand, sim in zip(candidates, sims):
        t1 = time.perf_counter()
        r = score_candidate(job, cand, sim)
        app = existing.get(cand.id)
        if app is None:
            app = Application(job_id=job.id, candidate_id=cand.id)
            db.add(app)
        app.score = r.score
        app.match_band = r.band
        app.breakdown = r.breakdown
        app.matched_skills = r.matched
        app.missing_skills = r.missing
        app.matched_preferred = r.matched_preferred
        app.explanation = r.explanation
        app.engine = engine
        app.matched_at = utcnow()
        app.match_ms = round(per_ms + (time.perf_counter() - t1) * 1000, 2)
        app.job = job
        app.candidate = cand
        route(app)
        out.append(app)
    db.commit()
    return out


# ---------------------------------------------------------------- Auto Apply (candidate opt-in for all jobs)
def is_auto_applied(app: Application) -> bool:
    return bool(app.candidate_applied and app.auto_apply and app.submitted_at)


def auto_apply_if_high(app: Application) -> bool:
    """Apply on the candidate's behalf when they turned on Auto Apply for all jobs (with consent
    given in "My Resume") and this open job scores 80%+. HR-locked decisions are never changed.
    Returns True when the application was newly submitted."""
    cand, job = app.candidate, app.job
    if not cand.auto_apply_all or job.status != "active" or app.status_locked:
        return False
    if app.score < HIGH_THRESHOLD or is_auto_applied(app):
        return False
    app.candidate_applied = True
    app.details_reviewed = True
    app.data_sharing_consent = True
    app.auto_apply = True
    route(app)
    return is_auto_applied(app)  # submitted (and possibly auto-shortlisted too)


def auto_apply_candidates_to_job(db, job: Job) -> list[Application]:
    """Score every Auto Apply candidate against an open job and apply where they score 80%+."""
    if job.status != "active":
        return []
    cands = db.query(Candidate).filter(Candidate.auto_apply_all.is_(True), Candidate.resume_text != "").all()
    newly = [a for a in run_matching(db, job, cands) if auto_apply_if_high(a)]
    db.commit()
    return newly


# ---------------------------------------------------------------- HR Auto Shortlist setting
def load_settings(db) -> None:
    row = db.get(Setting, "auto_shortlist")
    AUTO_SHORTLIST["on"] = bool(row and row.value == "1")


def set_auto_shortlist(db, on: bool) -> int:
    """Turn HR Auto Shortlist on or off and return how many applications it affected.

    On: every open application scoring 80%+ that HR has not decided on is shortlisted now.
    Off: applications it already shortlisted stay shortlisted (kept as a recruiter decision).
    """
    row = db.get(Setting, "auto_shortlist") or Setting(key="auto_shortlist")
    row.value = "1" if on else "0"
    db.add(row)
    AUTO_SHORTLIST["on"] = on
    changed = 0
    if on:
        for a in db.query(Application).filter(Application.status_locked.is_(False), Application.score >= HIGH_THRESHOLD):
            before = a.status
            route(a)
            changed += a.status == "shortlisted" and before != "shortlisted"
    else:
        for a in db.query(Application).filter(Application.status == "shortlisted", Application.status_locked.is_(False)):
            a.status_locked = True
            changed += 1
    db.commit()
    return changed
