from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .services.skills import normalize_skills

JobStatus = Literal["draft", "active", "closed"]
AppStatus = Literal[
    "submitted", "pending_consent", "recruiter_review", "standard_review", "shortlisted", "rejected"
]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ jobs
class JobIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: str = ""
    department: str = ""
    location: str = ""
    employment_type: str = "Full-time"
    description: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience: float = Field(default=0, ge=0, le=40)
    education_level: int = Field(default=0, ge=0, le=4)
    status: JobStatus = "active"

    @field_validator("required_skills", "preferred_skills")
    @classmethod
    def _norm(cls, v: list[str]) -> list[str]:
        return normalize_skills(v)


class JobOut(ORM):
    id: int
    title: str
    company: str
    department: str
    location: str
    employment_type: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience: float
    education_level: int
    status: str
    created_at: datetime
    updated_at: datetime
    candidates_matched: int = 0
    avg_score: float | None = None
    high_matches: int = 0


# ------------------------------------------------------------------ candidates
class CandidateUpdate(BaseModel):
    """Recruiter corrections of parsed data. (Consent is set only by the candidate.)"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    skills: list[str] | None = None
    education: list[dict] | None = None
    experience_years: float | None = Field(default=None, ge=0, le=50)

    @field_validator("skills")
    @classmethod
    def _norm(cls, v):
        return normalize_skills(v) if v is not None else v


class AppBrief(ORM):
    id: int
    job_id: int
    job_title: str
    score: float
    match_band: str
    status: str


class CandidateOut(ORM):
    id: int
    name: str
    email: str | None
    phone: str | None
    resume_filename: str | None
    skills: list[str]
    education: list[dict]
    experience_years: float
    corrected: bool
    auto_apply: bool
    details_reviewed: bool
    data_sharing_consent: bool
    created_at: datetime
    best_score: float | None = None
    applications: list[AppBrief] = Field(default_factory=list)


class CandidateDetail(CandidateOut):
    resume_text: str


class UploadResult(BaseModel):
    created: list[CandidateOut]
    errors: list[dict]
    matched_job_id: int | None = None


# ------------------------------------------------------------------ applications / matching
class ApplicationOut(ORM):
    candidate_applied: bool = False
    id: int
    job_id: int
    job_title: str
    candidate_id: int
    candidate_name: str
    candidate_email: str | None
    experience_years: float
    score: float
    match_band: str
    breakdown: dict
    matched_skills: list[str]
    missing_skills: list[str]
    matched_preferred: list[str]
    explanation: str
    engine: str
    status: str
    routing_reason: str
    recruiter_notes: str
    status_locked: bool
    auto_apply: bool
    details_reviewed: bool
    data_sharing_consent: bool
    submitted_at: datetime | None
    matched_at: datetime
    updated_at: datetime


class ApplicationUpdate(BaseModel):
    status: AppStatus | None = None
    recruiter_notes: str | None = Field(default=None, max_length=5000)
    reset_to_auto: bool = False  # clear a recruiter decision and re-apply routing rules


class MatchRunOut(BaseModel):
    job_id: int
    processed: int
    engine: str
    duration_ms: float
    results: list[ApplicationOut]
