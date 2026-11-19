from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    department: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    employment_type: Mapped[str] = mapped_column(String(40), default="Full-time")
    description: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list)
    min_experience: Mapped[float] = mapped_column(Float, default=0.0)
    education_level: Mapped[int] = mapped_column(Integer, default=0)  # 0 any .. 4 PhD
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # draft|active|closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resume_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    resume_text: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    parse_ms: Mapped[float] = mapped_column(Float, default=0.0)
    corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    # Candidate consent / Auto Apply controls (all must be true to auto-submit)
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    details_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    data_sharing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class Application(Base):
    """A candidate evaluated against a job: match result + workflow status."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)

    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    matched_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list)
    matched_preferred: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    match_band: Mapped[str] = mapped_column(String(10), default="low")  # high|medium|low
    engine: Mapped[str] = mapped_column(String(60), default="")
    match_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # submitted | pending_consent | recruiter_review | standard_review | shortlisted | rejected
    status: Mapped[str] = mapped_column(String(30), default="standard_review", index=True)
    routing_reason: Mapped[str] = mapped_column(Text, default="")
    recruiter_notes: Mapped[str] = mapped_column(Text, default="")
    status_locked: Mapped[bool] = mapped_column(Boolean, default=False)  # set by a recruiter decision
    candidate_applied: Mapped[bool] = mapped_column(Boolean, default=False)  # applied via portal (vs. HR screening)
    # Consent is given per job, by the candidate, when they apply. It never carries over to other jobs.
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    details_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    data_sharing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[Job] = relationship(back_populates="applications")
    candidate: Mapped[Candidate] = relationship(back_populates="applications")


class User(Base):
    """Login account. role = "hr" (recruiter dashboard) or "candidate" (candidate portal)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    candidate: Mapped[Candidate | None] = relationship()


class PasswordReset(Base):
    """One pending password-reset code per user. Only an HMAC of the code is stored."""

    __tablename__ = "password_resets"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
