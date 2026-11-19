"""Demo data: sample job descriptions and generated sample PDF resumes.

All people below are fictional. Run directly to (re)generate the sample PDFs:
    python -m app.seed            # generate PDFs + seed DB if empty
    python -m app.seed --reset    # wipe DB and re-seed
"""
from __future__ import annotations

import hashlib
import sys
import uuid
from pathlib import Path

from .database import DATA_DIR, UPLOAD_DIR
from .models import Candidate, Job

SAMPLE_DIR = DATA_DIR / "demo_resumes"  # demo-only PDFs; user-facing samples live in sample_resumes/

JOBS = [
    dict(
        title="Python Backend Developer", company="Acme Tech", department="Engineering",
        location="Bengaluru / Hybrid",
        description=(
            "We are looking for a Python backend developer to design and build REST APIs and microservices "
            "using FastAPI. You will work with MySQL databases, write clean tested code, use Git, and "
            "containerise services with Docker. Experience deploying services to cloud is a plus."
        ),
        required_skills=["Python", "FastAPI", "MySQL", "REST API", "Git", "Docker"],
        preferred_skills=["Kubernetes", "AWS", "Redis"], min_experience=2, education_level=2,
    ),
    dict(
        title="Frontend React Developer", company="Acme Tech", department="Engineering", location="Remote",
        description=(
            "Build responsive, accessible web interfaces with React and TypeScript. Collaborate with designers "
            "in Figma, manage state with Redux, style with Tailwind CSS and consume REST APIs."
        ),
        required_skills=["React", "JavaScript", "TypeScript", "HTML", "CSS", "REST API"],
        preferred_skills=["Redux", "Tailwind CSS", "Jest", "Figma"], min_experience=1, education_level=2,
    ),
    dict(
        title="Data Analyst", company="Acme Tech", department="Analytics", location="Hyderabad",
        description=(
            "Analyse business data, build dashboards and reports. Strong SQL and Python (Pandas) skills, "
            "experience with Power BI or Tableau, statistics and data visualization."
        ),
        required_skills=["SQL", "Python", "Pandas", "Excel", "Statistics", "Power BI"],
        preferred_skills=["Tableau", "Machine Learning"], min_experience=1, education_level=2,
    ),
]

# name, email, years summary, degree line, skills line, experience entries, flags
RESUMES = [
    ("Rahul Kumar", "rahul.kumar@example.com", "Backend developer with 2.5 years of experience building Python services.",
     "B.Tech in Computer Science, 2021", "Python, FastAPI, MySQL, REST API, Git, SQLAlchemy, Pydantic, Linux",
     [("Software Engineer, Nimbus Labs", "Jun 2022 - Present", "Built REST APIs with FastAPI and MySQL; wrote pytest suites; code reviews on GitHub.")],
     dict(auto_apply=True, details_reviewed=True, data_sharing_consent=True)),
    ("Priya Sharma", "priya.sharma@example.com", "Python developer with 2 years of experience in web backends.",
     "B.E in Information Technology, 2022", "Python, Django, FastAPI, REST API, Git, MySQL, PostgreSQL",
     [("Backend Developer, Orbit Soft", "Jul 2022 - Present", "Developed Django and FastAPI REST services backed by MySQL and PostgreSQL.")],
     dict(auto_apply=True, details_reviewed=False, data_sharing_consent=False)),
    ("Arjun Mehta", "arjun.mehta@example.com", "Engineer with 3 years of experience in Python and APIs.",
     "B.Tech in Electronics, 2020", "Python, FastAPI, MySQL, Redis, AWS",
     [("Associate Engineer, Cloudline", "Aug 2020 - Sep 2023", "Maintained FastAPI services and MySQL schemas, deployed on AWS EC2.")],
     dict()),
    ("Sneha Nair", "sneha.nair@example.com", "Junior developer with 1.8 years of experience.",
     "BCA, 2022", "Python, REST API, Git, Flask, SQLite",
     [("Junior Developer, Brightpath", "Feb 2023 - Present", "Built small Flask REST API services and internal tools.")],
     dict()),
    ("Vikram Singh", "vikram.singh@example.com", "Senior backend engineer with 5 years of experience.",
     "M.Tech in Computer Science, 2019", "Python, FastAPI, Django, MySQL, PostgreSQL, Docker, Kubernetes, AWS, Redis, Git, REST API, Microservices",
     [("Senior Engineer, Finlytics", "Jan 2021 - Present", "Led microservices migration on Kubernetes; FastAPI, Docker, Redis."),
      ("Software Engineer, DataForge", "Jul 2019 - Dec 2020", "Built Django REST APIs on MySQL.")],
     dict(auto_apply=True, details_reviewed=True, data_sharing_consent=True)),
    ("Ananya Iyer", "ananya.iyer@example.com", "Frontend engineer with 3 years of experience crafting React apps.",
     "B.Tech in Computer Science, 2021", "React, TypeScript, JavaScript, HTML, CSS, Redux, Tailwind CSS, Jest, Figma, REST API, Git",
     [("Frontend Engineer, Pixelcraft", "Aug 2021 - Present", "Built design-system components in React + TypeScript with Tailwind CSS.")],
     dict(auto_apply=True, details_reviewed=True, data_sharing_consent=False)),
    ("Karthik Reddy", "karthik.reddy@example.com", "Web developer with 1.5 years of experience.",
     "B.Sc in Computer Science, 2022", "JavaScript, React, HTML, CSS, Vue.js, Git",
     [("Web Developer, Sitewave", "May 2023 - Present", "Built React and Vue.js landing pages and dashboards.")],
     dict()),
    ("Meera Joshi", "meera.joshi@example.com", "Data analyst with 2 years of experience turning data into decisions.",
     "M.Sc in Statistics, 2022", "SQL, Python, Pandas, NumPy, Excel, Power BI, Tableau, Statistics, Data Visualization",
     [("Data Analyst, RetailIQ", "Aug 2022 - Present", "Built Power BI dashboards; SQL and Pandas analysis of sales data.")],
     dict(auto_apply=True, details_reviewed=True, data_sharing_consent=True)),
    ("Rohan Das", "rohan.das@example.com", "Analyst with 1 year of experience in reporting.",
     "B.Com, 2023", "Excel, SQL, Power BI, Data Visualization",
     [("Business Analyst Intern, Quanta", "Jan 2024 - Present", "Weekly Excel and Power BI reports for finance team.")],
     dict()),
    ("Fatima Sheikh", "fatima.sheikh@example.com", "ML engineer with 2 years of experience.",
     "M.Tech in Artificial Intelligence, 2022", "Python, Pandas, NumPy, Scikit-learn, PyTorch, Machine Learning, NLP, SQL, Docker",
     [("ML Engineer, VisionAI", "Sep 2022 - Present", "Trained NLP models with PyTorch, served via Docker containers.")],
     dict()),
    ("Aditya Verma", "aditya.verma@example.com", "Full-stack developer with 4 years of experience.",
     "B.Tech in Information Technology, 2020", "JavaScript, TypeScript, React, Node.js, Express, MongoDB, Docker, AWS, REST API, Git, Python",
     [("Full Stack Developer, Shopnest", "Jul 2020 - Present", "Built React frontends and Node.js/Express REST APIs on MongoDB.")],
     dict()),
    ("Neha Gupta", "neha.gupta@example.com", "QA engineer with 3 years of experience in test automation.",
     "B.E in Computer Science, 2020", "Selenium, Python, Pytest, Jest, Git, Agile",
     [("QA Engineer, Testify", "Jun 2020 - Jun 2023", "Automated UI tests with Selenium and Pytest in Agile teams.")],
     dict()),
]


# Demo logins, created only when SEED_DEMO=1. Change or disable these before real use.
DEMO_ACCOUNTS = [
    {"role": "hr", "name": "HR Admin", "email": "hr@matchpoint.test", "password": "hr-demo-2026"},
    {"role": "candidate", "name": "Rahul Kumar", "email": "rahul.kumar@example.com", "password": "candidate-demo-2026",
     "candidate_email": "rahul.kumar@example.com", "applied_jobs": ["Python Backend Developer"]},
]


def _make_pdf(path: Path, name, email, summary, degree, skills, exps) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    st = getSampleStyleSheet()
    flow = [
        Paragraph(name, st["Title"]),
        Paragraph(f"{email} | +91 98765 4{sum(map(ord, name)) * 7 % 10000:04d}", st["Normal"]),
        Spacer(1, 10),
        Paragraph("Summary", st["Heading2"]), Paragraph(summary, st["Normal"]),
        Paragraph("Technical Skills", st["Heading2"]), Paragraph(skills, st["Normal"]),
        Paragraph("Experience", st["Heading2"]),
    ]
    for title, dates, desc in exps:
        flow += [Paragraph(f"<b>{title}</b>", st["Normal"]), Paragraph(dates, st["Normal"]),
                 Paragraph(desc, st["Normal"]), Spacer(1, 6)]
    flow += [Paragraph("Education", st["Heading2"]), Paragraph(degree, st["Normal"])]
    SimpleDocTemplate(str(path), pagesize=A4, title=f"{name} Resume").build(flow)


def generate_sample_pdfs() -> list[tuple[Path, dict]]:
    SAMPLE_DIR.mkdir(exist_ok=True)
    out = []
    for name, email, summary, degree, skills, exps, flags in RESUMES:
        p = SAMPLE_DIR / f"{name.replace(' ', '_')}_Resume.pdf"
        if not p.exists():
            _make_pdf(p, name, email, summary, degree, skills, exps)
        out.append((p, flags))
    return out


def seed_if_empty(db) -> bool:
    if db.query(Job).count() or db.query(Candidate).count():
        return False
    from .services.matcher import run_matching
    from .services.parser import parse_resume

    jobs = [Job(**j) for j in JOBS]
    db.add_all(jobs)
    cands = []
    for path, flags in generate_sample_pdfs():
        data = path.read_bytes()
        parsed = parse_resume(data)
        stored = f"{uuid.uuid4().hex}.pdf"
        (UPLOAD_DIR / stored).write_bytes(data)
        cands.append(Candidate(
            name=parsed.name or path.stem, email=parsed.email, phone=parsed.phone,
            resume_filename=path.name, resume_path=stored, resume_hash=hashlib.sha256(data).hexdigest(),
            resume_text=parsed.text, skills=parsed.skills, education=parsed.education,
            experience_years=parsed.experience_years, parse_ms=parsed.parse_ms, **flags,
        ))
    db.add_all(cands)
    db.commit()
    for j in jobs:
        run_matching(db, j, cands)
    # demo candidates with consent flags behave as if they applied to each job through the portal
    from .services.matcher import route

    for c in cands:
        if c.auto_apply or c.details_reviewed or c.data_sharing_consent:
            for a in c.applications:
                a.candidate_applied = True
                a.auto_apply, a.details_reviewed = c.auto_apply, c.details_reviewed
                a.data_sharing_consent = c.data_sharing_consent
                route(a)
    db.commit()
    return True


def reparse_all(db) -> int:
    """Re-run the parser on stored resume text (after parser improvements) and re-score.

    Profiles a recruiter/candidate corrected by hand are left untouched.
    """
    from .services.matcher import run_matching
    from .services.parser import extract_education, extract_experience_years
    from .services.skills import extract_skills

    cands = db.query(Candidate).filter(Candidate.corrected.is_(False), Candidate.resume_text != "").all()
    for c in cands:
        c.skills = extract_skills(c.resume_text)
        c.education = extract_education(c.resume_text)
        c.experience_years = extract_experience_years(c.resume_text)
    db.commit()
    for job in db.query(Job):
        apps_cands = [a.candidate for a in job.applications]
        if apps_cands:
            run_matching(db, job, apps_cands)
    return len(cands)


if __name__ == "__main__":
    from .database import Base, SessionLocal, engine

    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
        for f in UPLOAD_DIR.glob("*.pdf"):
            f.unlink()
    Base.metadata.create_all(engine)
    generate_sample_pdfs()
    with SessionLocal() as db:
        if "--reparse" in sys.argv:
            print(f"Re-parsed {reparse_all(db)} candidate(s) and re-scored their matches.")
        else:
            print("Seeded demo data." if seed_if_empty(db) else "Database not empty; skipped seeding.")
