"""End-to-end API tests. Run: python -m pytest -q  (from backend/)"""
import io
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="rm-test-")
os.environ["SEMANTIC_ENGINE"] = "tfidf"  # fast & deterministic for tests
os.environ["SEED_DEMO"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from app.main import app  # noqa: E402
from app.services.parser import extract_education, extract_experience_years  # noqa: E402
from app.services.skills import extract_skills  # noqa: E402


def make_pdf(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in lines:
        c.drawString(50, y, line)
        y -= 18
    c.save()
    return buf.getvalue()


STRONG = make_pdf([
    "Test Candidate", "test.candidate@example.com | +91 90000 11111",
    "Summary", "Backend engineer with 3 years of experience.",
    "Skills", "Python, FastAPI, MySQL, REST API, Git, Docker, Redis",
    "Experience", "Engineer, Foo Corp", "Jan 2021 - Dec 2023",
    "Education", "B.Tech in Computer Science, 2020",
])
WEAK = make_pdf([
    "Weak Fit", "weak.fit@example.com",
    "Skills", "Excel, Tableau",
    "Experience", "Analyst, Bar Ltd", "2023 - 2024",
    "Education", "B.Com, 2022",
])

JOB = {
    "title": "Backend Dev", "description": "Python FastAPI REST API services with MySQL and Docker",
    "required_skills": ["python", "fastapi", "MySQL", "rest api", "git", "docker"],
    "preferred_skills": ["Redis"], "min_experience": 2, "education_level": 2,
}


HR_LOGIN = {"email": "hr@test.local", "password": "test-hr-password", "role": "hr"}


@pytest.fixture(scope="module")
def client():
    """A TestClient signed in as HR."""
    from app.auth import create_user
    from app.database import SessionLocal

    with TestClient(app) as c:
        with SessionLocal() as db:
            create_user(db, email=HR_LOGIN["email"], name="Test HR", password=HR_LOGIN["password"], role="hr")
        assert c.post("/api/auth/login", json=HR_LOGIN).status_code == 200
        yield c


def candidate_client(email: str) -> TestClient:
    """A separate browser session for a newly registered candidate."""
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"name": "Portal User", "email": email, "password": "candidate-pw-1"})
    assert r.status_code == 201, r.text
    return c


def upload(client, data, name="r.pdf", **form):
    return client.post("/api/candidates/upload", files=[("files", (name, data, "application/pdf"))], data=form)


# ---------------------------------------------------------------- unit
def test_skill_extraction_boundaries():
    s = extract_skills("Java, JavaScript, MySQL and REST APIs; I rest on weekends. C++ and Node.js", with_implied=False)
    assert {"Java", "JavaScript", "MySQL", "REST API", "C++", "Node.js"} <= set(s)
    assert "SQL" not in s
    assert "REST API" not in extract_skills("I like to rest")


def test_education_and_experience():
    assert extract_education("B.E in Information Technology, 2022")[0]["degree"] == "B.E"
    assert extract_education("Biotech enthusiast") == []
    assert extract_experience_years("I have 4+ years of experience") == 4
    text = "Experience\nA, Jan 2020 - Dec 2020\nB, Jun 2020 - Dec 2021\nEducation\nB.Tech 2019"
    assert extract_experience_years(text) == 2.0  # overlapping ranges merged


# ---------------------------------------------------------------- e2e
def test_full_flow(client):
    job = client.post("/api/jobs", json=JOB).json()
    assert job["required_skills"] == ["Python", "FastAPI", "MySQL", "REST API", "Git", "Docker"]

    # HR upload of a high match: no candidate consent exists -> recruiter review, never auto-submitted
    r = upload(client, STRONG, "strong.pdf", job_id=job["id"])
    assert r.status_code == 200, r.text
    cand = r.json()["created"][0]
    assert cand["email"] == "test.candidate@example.com"
    assert cand["experience_years"] == 3
    a = client.get(f"/api/match/{job['id']}").json()[0]
    assert a["score"] >= 80 and a["match_band"] == "high" and a["missing_skills"] == []
    assert a["status"] == "recruiter_review"
    # recruiter cannot force-submit without the candidate's consent
    assert client.patch(f"/api/applications/{a['id']}", json={"status": "submitted"}).status_code == 400
    # HR cannot set consent on the candidate's behalf (field is ignored)
    client.patch(f"/api/candidates/{cand['id']}", json={"auto_apply": True, "data_sharing_consent": True})
    assert client.get(f"/api/candidates/{cand['id']}").json()["auto_apply"] is False

    # low match -> standard_review
    weak = upload(client, WEAK, "weak.pdf", job_id=job["id"]).json()["created"][0]
    wa = client.get("/api/applications", params={"candidate_id": weak["id"]}).json()[0]
    assert wa["score"] < 60 and wa["status"] == "standard_review"

    # parsing correction raises score and re-routes
    before = wa["score"]
    client.patch(f"/api/candidates/{weak['id']}", json={"skills": ["Python", "FastAPI", "MySQL", "REST API", "Git"], "experience_years": 3})
    wa2 = client.get(f"/api/applications/{wa['id']}").json()
    assert wa2["score"] > before
    assert client.get(f"/api/candidates/{weak['id']}").json()["corrected"] is True

    # recruiter decision is kept across re-matching, and can be undone
    client.patch(f"/api/applications/{wa['id']}", json={"status": "shortlisted", "recruiter_notes": "Strong interview"})
    client.post(f"/api/match/{job['id']}")
    wa3 = client.get(f"/api/applications/{wa['id']}").json()
    assert wa3["status"] == "shortlisted" and wa3["recruiter_notes"] == "Strong interview"
    wa4 = client.patch(f"/api/applications/{wa['id']}", json={"reset_to_auto": True}).json()
    assert wa4["status"] != "shortlisted"

    # dashboard + reports
    s = client.get("/api/stats").json()
    assert s["total_candidates"] == 2 and s["distribution"]["total"] == 2
    rep = client.get("/api/reports").json()
    assert sum(b["count"] for b in rep["score_histogram"]) == 2


def test_upload_validation(client):
    r = client.post("/api/candidates/upload", files=[("files", ("x.pdf", b"not a pdf", "application/pdf"))]).json()
    assert r["created"] == [] and "not a valid PDF" in r["errors"][0]["error"]
    r = client.post("/api/candidates/upload", files=[("files", ("x.txt", b"hello", "text/plain"))]).json()
    assert "Only PDF" in r["errors"][0]["error"]
    # duplicate detection
    r = upload(client, STRONG, "again.pdf").json()
    assert "Duplicate" in r["errors"][0]["error"]


def test_job_edit_rescores_and_status(client):
    job = client.post("/api/jobs", json={**JOB, "title": "Edit Me"}).json()
    client.post(f"/api/match/{job['id']}")
    edited = client.put(f"/api/jobs/{job['id']}", json={**JOB, "title": "Edit Me", "required_skills": ["Kubernetes"]}).json()
    assert edited["required_skills"] == ["Kubernetes"]
    res = client.get(f"/api/match/{job['id']}").json()
    assert all(r["missing_skills"] == ["Kubernetes"] for r in res)
    assert client.patch(f"/api/jobs/{job['id']}/status", params={"status": "closed"}).json()["status"] == "closed"
    # uploading to a closed job is rejected
    assert upload(client, make_pdf(["New Person", "new@example.com", "Skills", "Python"]), job_id=job["id"]).status_code == 400
    assert client.delete(f"/api/jobs/{job['id']}").status_code == 204


def test_correction_does_not_add_jobs(client):
    j1 = client.post("/api/jobs", json={**JOB, "title": "Only This"}).json()
    client.post("/api/jobs", json={**JOB, "title": "Other Active"})
    pdf = make_pdf(["Solo Applicant", "solo@example.com", "Skills", "Python, FastAPI", "Experience", "2020 - 2023"])
    cid = upload(client, pdf, "solo.pdf", job_id=j1["id"]).json()["created"][0]["id"]
    client.patch(f"/api/candidates/{cid}", json={"skills": ["Python", "FastAPI", "Docker"]})
    apps = client.get("/api/applications", params={"candidate_id": cid}).json()
    assert [a["job_id"] for a in apps] == [j1["id"]]


# ---------------------------------------------------------------- real-world formats
from datetime import date as _date  # noqa: E402

_TODAY = _date(2026, 11, 19)


@pytest.mark.parametrize("text, years", [
    ("Experience\nDev, Acme\nJan 2022 - Present\nEducation", 4.9),
    ("Experience\nDev, Acme\n06/2021 - 08/2023\nEducation", 2.2),
    ("Experience\nDev, Acme\n06-2021 to 08-2023\nEducation", 2.2),
    ("Experience\nDev, Acme\nJune 2021 – Aug 2023", 2.2),
    ("Experience\nDev\nJan ’21 - Mar ’22", 1.2),
    ("Software Engineer at Acme (2020 - 2023)", 4.0),  # no section heading
    ("PROFESSIONAL EXPERIENCE\nDev\nJan 2020 - Dec 2022\nEDUCATION", 3.0),
    ("Work Experience:\nSept 2019 - Present", 7.2),
    ("Experience\nDev 2019-2021", 3.0),
    ("Experience\nA, Jan 2020 - Dec 2020\nB, Jun 2020 - Dec 2021", 2.0),  # overlap merged
    ("Education\nB.Tech, ABC University\n2016 - 2020\nExperience\nDev\nJan 2021 - Dec 2022", 2.0),
    ("B.Tech, ABC University\n2016 - 2020\nDeveloper at Acme, 2023 - 2023", 1.0),  # study years ignored
    ("Experience\nDev, X\n2024 - 2024\nProjects\nChat app\n2019 - 2023", 1.0),  # project dates ignored
    ("Experience\nJan 2026 - Dec 2027", 0.9),  # future end clamped to today
    ("Summary\nI have 5+ years of experience", 5.0),
])
def test_experience_formats(text, years):
    assert extract_experience_years(text, today=_TODAY) == years


def test_modern_skills_recognised():
    text = ("Next.js, NestJS, Prisma, Supabase, LangChain, Hugging Face, OpenCV, Kafka, RabbitMQ, "
            "Snowflake, dbt, Airflow, Postman, JIRA, GitHub Actions, Terraform, Playwright")
    found = set(extract_skills(text, with_implied=False))
    assert {"Next.js", "NestJS", "Prisma", "LangChain", "Kafka", "Airflow", "JIRA", "GitHub Actions", "Playwright"} <= found
    assert "JavaScript" not in found  # "js" inside "Next.js" is not JavaScript


@pytest.mark.parametrize("text", [
    "I excel at teamwork and express ideas clearly.",
    "In spring 2022 I took a rest.",
    "Grade: C in physics. R&D team. Go-to-market plan. John R. Smith.",
    "Used Python lambda functions.",
])
def test_no_false_positive_skills(text):
    found = set(extract_skills(text, with_implied=False))
    assert not found & {"Excel", "Express", "Spring Boot", "REST API", "C", "R", "Go", "AWS"}


def test_short_skills_in_lists_and_implied():
    assert {"C", "Go", "R", "C++"} <= set(extract_skills("Languages: C, C++, Go, R"))
    found = extract_skills("Django, Jenkins, GitHub")
    assert {"Python", "CI/CD", "Git"} <= set(found)


# ---------------------------------------------------------------- auth & candidate portal
def test_hr_api_requires_hr_login(client):
    anon = TestClient(app)
    assert anon.get("/api/jobs").status_code == 401
    assert anon.get("/api/health").status_code == 200
    cand = candidate_client("nosy@example.com")
    for path in ["/api/jobs", "/api/candidates", "/api/applications", "/api/stats", "/api/reports"]:
        assert cand.get(path).status_code == 403, path
    # HR accounts cannot self-register; register always creates a candidate
    assert cand.get("/api/auth/me").json() == {"hr": None, "candidate": cand.get("/api/auth/me").json()["candidate"]}
    assert cand.get("/api/auth/me").json()["candidate"]["role"] == "candidate"


def test_login_errors_and_rate_limit(client):
    anon = TestClient(app)
    assert anon.post("/api/auth/login", json={**HR_LOGIN, "password": "wrong"}).status_code == 401
    for _ in range(8):
        anon.post("/api/auth/login", json={"email": "victim@example.com", "password": "x"})
    assert anon.post("/api/auth/login", json={"email": "victim@example.com", "password": "x"}).status_code == 429
    # tampered session cookie is rejected
    anon.cookies.set("mp_hr", "eyJ1aWQiOjEsInJvbGUiOiJociIsImV4cCI6OTk5OTk5OTk5OX0.forged")
    assert anon.get("/api/jobs").status_code == 401


def test_candidate_portal_flow(client):
    job = client.post("/api/jobs", json={**JOB, "title": "Portal Job"}).json()
    other = client.post("/api/jobs", json={**JOB, "title": "Not Applied"}).json()
    me = candidate_client("portal.user@example.com")

    jobs = me.get("/api/portal/jobs").json()
    assert {j["title"] for j in jobs} >= {"Portal Job", "Not Applied"}
    # must upload a resume first, and consent is required to apply
    consent = {"details_reviewed": True, "data_sharing_consent": True, "auto_apply": True}
    assert me.post(f"/api/portal/apply/{job['id']}", json=consent).status_code == 400
    r = me.post("/api/portal/resume", files={"file": ("cv.pdf", STRONG, "application/pdf")})
    assert r.status_code == 200 and r.json()["experience_years"] == 3
    assert me.post(f"/api/portal/apply/{job['id']}", json={**consent, "data_sharing_consent": False}).status_code == 400

    # high match + Auto Apply + consent -> submitted (visible to HR)
    res = me.post(f"/api/portal/apply/{job['id']}", json=consent).json()
    assert res["score"] >= 80 and res["explanation"] and res["missing_skills"] == []
    assert "status" not in res and "recruiter_notes" not in res  # candidates see score + explanation only
    hr_view = client.get("/api/applications", params={"job_id": job["id"]}).json()
    mine = next(a for a in hr_view if a["candidate_email"] == "portal.user@example.com")
    assert mine["status"] == "submitted"

    # the resume is scored for every open job, but only the job they applied to counts as applied
    client.post(f"/api/match/{other['id']}")
    results = me.get("/api/portal/results").json()
    assert {"Portal Job", "Not Applied"} <= {r["job_title"] for r in results}
    assert [r["job_title"] for r in results if r["applied"]] == ["Portal Job"]
    assert results[0]["job_title"] == "Portal Job" and results[0]["auto_applied"]

    # replacing the resume re-scores the application
    me.post("/api/portal/resume", files={"file": ("cv2.pdf", WEAK, "application/pdf")})
    assert me.get("/api/portal/results").json()[0]["score"] < res["score"]

    # a candidate can never read another candidate's data
    assert me.get(f"/api/candidates/{mine['candidate_id']}").status_code == 403


def test_unknown_api_path_is_json_404_and_not_cached(client):
    r = TestClient(app).get("/api/does-not-exist")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")
    assert client.get("/api/jobs").headers["cache-control"] == "no-store"


# ---------------------------------------------------------------- template-style sample resumes
from pathlib import Path as _Path  # noqa: E402

from app.services.parser import parse_resume  # noqa: E402

_SAMPLES = _Path(__file__).resolve().parents[1] / "sample_resumes"


@pytest.mark.parametrize("stem, name, email, years, degree, must_have", [
    ("01_Aarav_Nair_Python_Backend", "Aarav Nair", "aarav.nair@example.com", 6, "B.Tech", {"FastAPI", "MySQL", "Docker"}),
    ("02_Diya_Kapoor_Frontend_React", "Diya Kapoor", "diya.kapoor@example.com", 5, "B.E", {"React", "TypeScript", "Tailwind CSS"}),
    ("03_Kabir_Sethi_Data_Analyst", "Kabir Sethi", "kabir.sethi@example.com", 4.5, "M.Sc", {"SQL", "Pandas", "Power BI", "Excel"}),
    ("04_Meher_Ali_DevOps", "Meher Ali", "meher.ali@example.com", 7, "B.Tech", {"Kubernetes", "Terraform", "AWS"}),
    ("05_Ira_Menon_ML_Engineer", "Ira Menon", "ira.menon@example.com", 4.9, "M.Tech", {"PyTorch", "LangChain", "NLP"}),
    ("06_Rohit_Bansal_Fresher_Python", "Rohit Bansal", "rohit.bansal@example.com", 0.5, "B.Tech", {"Python", "FastAPI", "Git"}),
    ("07_Sana_Qureshi_Fullstack", "Sana Qureshi", "sana.qureshi@example.com", 5.5, "MCA", {"React", "Node.js", "MongoDB"}),
    ("08_Vivek_Raman_Senior_Backend_Java", "Vivek Raman", "vivek.raman@example.com", 10, "B.E", {"Java", "Spring Boot", "Kafka"}),
    ("09_Tara_Fernandes_QA_Automation", "Tara Fernandes", "tara.fernandes@example.com", 6, "B.Sc", {"Selenium", "Playwright", "Postman"}),
    ("10_Nikhil_Joshi_Data_Engineer", "Nikhil Joshi", "nikhil.joshi@example.com", 5, "B.Tech", {"Spark", "Airflow", "Snowflake"}),
])
def test_sample_resume_templates_parse(stem, name, email, years, degree, must_have):
    path = _SAMPLES / f"{stem}.pdf"
    if not path.exists():
        pytest.skip("run scripts/make_sample_resumes.py to generate sample resumes")
    r = parse_resume(path.read_bytes())
    assert (r.name, r.email, r.experience_years) == (name, email, years)
    assert r.education[0]["degree"] == degree
    assert must_have <= set(r.skills)


def test_hr_and_candidate_sessions_coexist_in_one_browser(client):
    """One browser (one cookie jar) signed in as HR and as a candidate in different tabs."""
    browser = candidate_client("two.tabs@example.com")           # tab 1: candidate portal
    assert browser.get("/api/portal/jobs").status_code == 200
    assert browser.get("/api/jobs").status_code == 403            # not HR yet

    assert browser.post("/api/auth/login", json=HR_LOGIN).status_code == 200  # tab 2: HR signs in
    me = browser.get("/api/auth/me").json()
    assert me["hr"]["role"] == "hr" and me["candidate"]["email"] == "two.tabs@example.com"
    assert browser.get("/api/jobs").status_code == 200            # HR dashboard works
    assert browser.get("/api/portal/jobs").status_code == 200     # candidate tab still works

    browser.post("/api/auth/logout", params={"role": "hr"})       # sign out of HR only
    assert browser.get("/api/jobs").status_code == 403
    assert browser.get("/api/portal/jobs").status_code == 200     # candidate unaffected

    browser.post("/api/auth/logout")                              # sign out of everything
    assert browser.get("/api/auth/me").json() == {"hr": None, "candidate": None}


def test_each_login_page_only_accepts_its_own_role(client):
    anon = TestClient(app)
    # HR account on the candidate sign-in page: rejected exactly like a wrong password
    r = anon.post("/api/auth/login", json={**HR_LOGIN, "role": "candidate"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect email or password."
    # candidate account on the HR sign-in page: rejected the same way
    candidate_client("portal.only@example.com")
    r = anon.post("/api/auth/login", json={"email": "portal.only@example.com", "password": "candidate-pw-1", "role": "hr"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect email or password."
    # and each works on its own page
    assert anon.post("/api/auth/login", json={"email": "portal.only@example.com", "password": "candidate-pw-1"}).status_code == 200
    assert anon.post("/api/auth/login", json=HR_LOGIN).status_code == 200


# ---------------------------------------------------------------- deployment hardening
def test_security_headers(client):
    page = TestClient(app).get("/api/does-not-exist")
    for h in ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy"]:
        assert h in page.headers, h
    assert "Strict-Transport-Security" not in page.headers  # only sent over HTTPS
    https = TestClient(app, base_url="https://testserver")
    assert "max-age" in https.get("/api/health").headers["Strict-Transport-Security"]


def test_production_mode_hardening(tmp_path):
    """APP_ENV=production: docs hidden, demo off, cookies always Secure. Runs in a fresh process."""
    import subprocess
    import sys as _sys

    script = """
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_user
from app.database import SessionLocal
with TestClient(app) as c:
    assert 'swagger' not in c.get('/docs').text.lower(), 'docs visible'
    assert '"openapi"' not in c.get('/openapi.json').text, 'openapi schema visible'
    assert 'redoc' not in c.get('/redoc').text.lower(), 'redoc visible'
    with SessionLocal() as db:
        from app.models import User, Job
        assert db.query(Job).count() == 0 and db.query(User).count() == 0, 'demo data seeded'
        create_user(db, email='p@x.test', name='P', password='prod-pass-123', role='hr')
    r = c.post('/api/auth/login', json={'email': 'p@x.test', 'password': 'prod-pass-123', 'role': 'hr'})
    cookie = r.headers['set-cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie, cookie
print('ok')
"""
    env = {**os.environ, "APP_ENV": "production", "DATA_DIR": str(tmp_path), "SEMANTIC_ENGINE": "tfidf"}
    env.pop("SEED_DEMO", None)
    out = subprocess.run([_sys.executable, "-c", script], cwd=_Path(__file__).resolve().parents[1],
                         env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr[-2000:]


def test_forgot_password_otp_flow(client, monkeypatch):
    import re

    import app.auth as auth_mod

    sent = []
    monkeypatch.setattr(auth_mod, "send_email", lambda to, subject, text, html=None: sent.append((to, text)) or True)
    monkeypatch.setattr(auth_mod, "RESEND_SECONDS", 0)
    email = "reset.me@example.com"
    old = candidate_client(email)
    assert old.get("/api/portal/me").status_code == 200

    # unknown email and wrong-portal email get the same answer, and no email is sent
    same = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com", "role": "candidate"}).json()
    assert client.post("/api/auth/forgot-password", json={"email": HR_LOGIN["email"], "role": "candidate"}).json() == same
    assert sent == []

    r = client.post("/api/auth/forgot-password", json={"email": email.upper(), "role": "candidate"})
    assert r.status_code == 200 and r.json() == same
    assert len(sent) == 1 and sent[0][0] == email
    code = re.search(r"\b(\d{6})\b", sent[0][1]).group(1)

    bad = f"{(int(code) + 1) % 1_000_000:06d}"
    r = client.post("/api/auth/reset-password", json={"email": email, "role": "candidate", "code": bad, "password": "brand-new-pw"})
    assert r.status_code == 400 and "4 attempts left" in r.json()["detail"]
    # the code only works on the matching portal
    r = client.post("/api/auth/reset-password", json={"email": email, "role": "hr", "code": code, "password": "brand-new-pw"})
    assert r.status_code == 400
    assert client.post("/api/auth/reset-password", json={"email": email, "role": "candidate", "code": code, "password": "short"}).status_code == 422

    r = client.post("/api/auth/reset-password", json={"email": email, "role": "candidate", "code": code, "password": "brand-new-pw"})
    assert r.status_code == 200, r.text
    # code is single-use; old password and old sessions stop working; new password works
    assert client.post("/api/auth/reset-password", json={"email": email, "role": "candidate", "code": code, "password": "another-pw-1"}).status_code == 400
    assert old.get("/api/portal/me").status_code == 401
    fresh = TestClient(app)
    assert fresh.post("/api/auth/login", json={"email": email, "password": "candidate-pw-1", "role": "candidate"}).status_code == 401
    assert fresh.post("/api/auth/login", json={"email": email, "password": "brand-new-pw", "role": "candidate"}).status_code == 200
    assert client.get("/api/stats").status_code == 200  # HR session untouched


def test_reset_code_locks_after_five_wrong_tries(client, monkeypatch):
    import re

    import app.auth as auth_mod

    sent = []
    monkeypatch.setattr(auth_mod, "send_email", lambda to, subject, text, html=None: sent.append(text) or True)
    email = "lock.me@example.com"
    candidate_client(email)
    c = TestClient(app)
    c.post("/api/auth/forgot-password", json={"email": email, "role": "candidate"})
    code = re.search(r"\b(\d{6})\b", sent[0]).group(1)
    assert c.post("/api/auth/forgot-password", json={"email": email, "role": "candidate"}).status_code == 429  # resend cooldown
    bad = f"{(int(code) + 1) % 1_000_000:06d}"
    for _ in range(5):
        assert c.post("/api/auth/reset-password", json={"email": email, "role": "candidate", "code": bad, "password": "brand-new-pw"}).status_code == 400
    r = c.post("/api/auth/reset-password", json={"email": email, "role": "candidate", "code": code, "password": "brand-new-pw"})
    assert r.status_code == 400  # even the right code is dead after 5 wrong tries


CONSENT = {"details_reviewed": True, "data_sharing_consent": True, "auto_apply": True}


def test_consent_is_per_job_not_carried_to_other_jobs(client):
    a = client.post("/api/jobs", json={**JOB, "title": "Consent Job A"}).json()["id"]
    b = client.post("/api/jobs", json={**JOB, "title": "Consent Job B"}).json()["id"]
    me = candidate_client("per.job@example.com")
    assert me.post("/api/portal/resume", files={"file": ("cv.pdf", make_pdf(
        ["Per Job", "per.job@example.com", "Skills", "Python, FastAPI, MySQL, REST API, Git, Docker, Redis",
         "Experience", "Engineer, Foo Corp", "Jan 2019 - Dec 2023", "Education", "B.Tech in Computer Science, 2018"]),
        "application/pdf")}).status_code == 200
    r = me.post(f"/api/portal/apply/{a}", json=CONSENT).json()
    assert r["score"] >= 80

    # HR screening the same candidate for job B must NOT use the consent given for job A
    res = {x["candidate_email"]: x for x in client.post(f"/api/match/{b}").json()["results"]}
    on_b = res["per.job@example.com"]
    assert on_b["score"] >= 80 and on_b["status"] == "recruiter_review" and not on_b["candidate_applied"]
    assert client.patch(f"/api/applications/{on_b['id']}", json={"status": "submitted"}).status_code == 400
    on_a = [x for x in client.get(f"/api/match/{a}").json() if x["candidate_email"] == "per.job@example.com"][0]
    assert on_a["status"] == "submitted" and on_a["candidate_applied"] and on_a["auto_apply"]

    # applying to B without Auto Apply leaves A submitted, and B goes to review
    r = me.post(f"/api/portal/apply/{b}", json={**CONSENT, "auto_apply": False})
    assert r.status_code == 200
    statuses = {x["job_id"]: x["status"] for x in client.get("/api/applications").json()
                if x["candidate_email"] == "per.job@example.com"}
    assert statuses[a] == "submitted" and statuses[b] == "recruiter_review"
    me.post("/api/portal/resume", files={"file": ("cv2.pdf", make_pdf(
        ["Per Job", "per.job@example.com", "Skills", "Python, FastAPI, MySQL, REST API, Git, Docker, Redis",
         "Experience", "Engineer, Foo Corp", "Jan 2019 - Dec 2023", "Education", "B.Tech in Computer Science, 2018",
         "Certified"]), "application/pdf")})
    statuses = {x["job_id"]: x["status"] for x in client.get("/api/applications").json()
                if x["candidate_email"] == "per.job@example.com"}
    assert statuses[a] == "submitted"  # re-scoring after a new resume keeps A's own consent


AUTO_PDF = make_pdf(
    ["Auto Applier", "auto.applier@example.com", "Skills", "Python, FastAPI, MySQL, REST API, Git, Docker, Redis",
     "Experience", "Engineer, Foo Corp", "Jan 2019 - Dec 2023", "Education", "B.Tech in Computer Science, 2018"])


def test_upload_scores_every_open_job(client):
    fit = client.post("/api/jobs", json={**JOB, "title": "Score All Fit"}).json()["id"]
    misfit = client.post("/api/jobs", json={**JOB, "title": "Score All Misfit", "required_skills": ["Excel", "Tableau"],
                                            "preferred_skills": [], "description": "Spreadsheets"}).json()["id"]
    closed = client.post("/api/jobs", json={**JOB, "title": "Score All Closed", "status": "closed"}).json()["id"]
    me = candidate_client("score.all@example.com")
    assert me.post("/api/portal/resume", files={"file": ("cv.pdf", AUTO_PDF, "application/pdf")}).status_code == 200

    jobs = {j["id"]: j for j in me.get("/api/portal/jobs").json()}
    assert jobs[fit]["score"] >= 80 and jobs[misfit]["score"] < 60
    assert not jobs[fit]["applied"] and not jobs[fit]["auto_applied"]  # Auto Apply is off: scored, not applied
    assert closed not in jobs
    results = {r["job_id"]: r for r in me.get("/api/portal/results").json()}
    assert {fit, misfit} <= set(results) and closed not in results
    # HR sees the screening result but it was not submitted
    hr = [a for a in client.get("/api/applications", params={"job_id": fit}).json() if a["candidate_email"] == "score.all@example.com"][0]
    assert hr["status"] == "recruiter_review" and not hr["candidate_applied"]


def test_auto_apply_applies_to_high_matches_only(client):
    high = client.post("/api/jobs", json={**JOB, "title": "Auto High"}).json()["id"]
    low = client.post("/api/jobs", json={**JOB, "title": "Auto Low", "required_skills": ["Excel", "Tableau"],
                                         "preferred_skills": [], "description": "Spreadsheets"}).json()["id"]
    me = candidate_client("auto.applier@example.com")

    # needs a resume and both consents
    assert me.post("/api/portal/auto-apply", json={"enabled": True, "details_reviewed": True, "data_sharing_consent": True}).status_code == 400
    me.post("/api/portal/resume", files={"file": ("cv.pdf", AUTO_PDF, "application/pdf")})
    assert me.post("/api/portal/auto-apply", json={"enabled": True, "details_reviewed": True}).status_code == 400

    r = me.post("/api/portal/auto-apply", json={"enabled": True, "details_reviewed": True, "data_sharing_consent": True})
    assert r.status_code == 200 and r.json()["auto_apply_all"] and "Auto High" in r.json()["auto_applied_jobs"]
    assert "Auto Low" not in r.json()["auto_applied_jobs"]
    status = {a["job_id"]: a for a in client.get("/api/applications").json() if a["candidate_email"] == "auto.applier@example.com"}
    assert status[high]["status"] == "submitted" and status[high]["candidate_applied"]
    assert status[low]["status"] == "standard_review" and not status[low]["candidate_applied"]
    jobs = {j["id"]: j for j in me.get("/api/portal/jobs").json()}
    assert jobs[high]["auto_applied"] and not jobs[low]["applied"]

    # a job HR posts later is scored and applied to straight away
    later = client.post("/api/jobs", json={**JOB, "title": "Auto Later"}).json()["id"]
    later_app = [a for a in client.get("/api/applications", params={"job_id": later}).json() if a["candidate_email"] == "auto.applier@example.com"][0]
    assert later_app["status"] == "submitted"

    # an HR decision is never overridden by a re-upload
    client.patch(f"/api/applications/{status[high]['id']}", json={"status": "rejected"})
    me.post("/api/portal/resume", files={"file": ("cv2.pdf", AUTO_PDF + b" ", "application/pdf")})
    assert client.get(f"/api/applications/{status[high]['id']}").json()["status"] == "rejected"

    # turning it off stops new auto-applications; submitted ones stay submitted
    assert me.post("/api/portal/auto-apply", json={"enabled": False}).json()["auto_apply_all"] is False
    off = client.post("/api/jobs", json={**JOB, "title": "Auto Off"}).json()["id"]
    assert not [a for a in client.get("/api/applications", params={"job_id": off}).json() if a["candidate_email"] == "auto.applier@example.com"]
    assert client.get(f"/api/applications/{later_app['id']}").json()["status"] == "submitted"


def test_hr_auto_shortlist(client):
    def apps_for(job_id):
        return {a["candidate_email"]: a for a in client.get("/api/applications", params={"job_id": job_id}).json()}

    job = client.post("/api/jobs", json={**JOB, "title": "Shortlist Job"}).json()["id"]
    strong = make_pdf(["Strong Shortlist", "strong.shortlist@example.com", "Skills",
                       "Python, FastAPI, MySQL, REST API, Git, Docker, Redis", "Experience", "Engineer, Foo Corp",
                       "Jan 2019 - Dec 2023", "Education", "B.Tech in Computer Science, 2018"])
    weak = make_pdf(["Weak Shortlist", "weak.shortlist@example.com", "Skills", "Excel", "Education", "B.Com, 2022"])
    decided = make_pdf(["Decided Already", "decided.already@example.com", "Skills",
                        "Python, FastAPI, MySQL, REST API, Git, Docker, Redis", "Experience", "Engineer, Bar Corp",
                        "Jan 2018 - Dec 2023", "Education", "B.Tech in Computer Science, 2017"])
    for pdf, name in ((strong, "s.pdf"), (weak, "w.pdf"), (decided, "d.pdf")):
        assert upload(client, pdf, name, job_id=str(job)).status_code == 200
    before = apps_for(job)
    assert before["strong.shortlist@example.com"]["status"] == "recruiter_review"
    rejected_id = before["decided.already@example.com"]["id"]
    client.patch(f"/api/applications/{rejected_id}", json={"status": "rejected"})

    assert client.get("/api/settings/auto-shortlist").json() == {"enabled": False, "threshold": 80}
    assert TestClient(app).put("/api/settings/auto-shortlist", json={"enabled": True}).status_code == 401  # HR only
    try:
        r = client.put("/api/settings/auto-shortlist", json={"enabled": True}).json()
        assert r["enabled"] and r["changed"] >= 1
        now = apps_for(job)
        assert now["strong.shortlist@example.com"]["status"] == "shortlisted"
        assert now["strong.shortlist@example.com"]["routing_reason"].startswith("Auto-shortlisted")
        assert now["weak.shortlist@example.com"]["status"] == "standard_review"  # low score: untouched
        assert now["decided.already@example.com"]["status"] == "rejected"  # HR decision is never overridden

        # new high matches are shortlisted as they arrive, from HR uploads and from the candidate portal
        me = candidate_client("portal.shortlist@example.com")
        me.post("/api/portal/resume", files={"file": ("cv.pdf", AUTO_PDF.replace(b"Auto Applier", b"Portal Short"), "application/pdf")})
        me.post(f"/api/portal/apply/{job}", json=CONSENT)
        mine = apps_for(job)["portal.shortlist@example.com"]
        assert mine["status"] == "shortlisted" and mine["candidate_applied"] and mine["submitted_at"]
        assert me.get("/api/portal/jobs").json() and [j for j in me.get("/api/portal/jobs").json() if j["id"] == job][0]["auto_applied"]

        # turning it off keeps what it shortlisted (now as a recruiter decision)
        off = client.put("/api/settings/auto-shortlist", json={"enabled": False}).json()
        assert not off["enabled"] and off["changed"] >= 2
        kept = apps_for(job)["strong.shortlist@example.com"]
        assert kept["status"] == "shortlisted" and kept["status_locked"]
        late = upload(client, make_pdf(["Late Strong", "late.strong@example.com", "Skills",
                                        "Python, FastAPI, MySQL, REST API, Git, Docker, Redis", "Experience",
                                        "Engineer, Baz", "Jan 2019 - Dec 2023", "Education", "B.Tech in CS, 2018"]),
                      "late.pdf", job_id=str(job))
        assert late.status_code == 200 and apps_for(job)["late.strong@example.com"]["status"] == "recruiter_review"
    finally:
        client.put("/api/settings/auto-shortlist", json={"enabled": False})


def test_portal_upload_links_to_hr_uploaded_profile(client):
    pdf = make_pdf(["Same Person", "same.person@example.com", "Skills", "Python, SQL", "Experience",
                    "Analyst, Q Ltd", "2021 - 2023", "Education", "B.Sc in Maths, 2020"])
    hr_up = upload(client, pdf, "same.pdf").json()["created"][0]
    me = candidate_client("same.person@example.com")
    assert me.post("/api/portal/resume", files={"file": ("mine.pdf", pdf, "application/pdf")}).status_code == 200
    matching = [c for c in client.get("/api/candidates", params={"search": "same.person@example.com"}).json()]
    assert len(matching) == 1 and matching[0]["id"] == hr_up["id"]  # one profile, not two


def test_change_password_signs_out_other_sessions(client):
    email = "changer@example.com"
    here = candidate_client(email)
    other = TestClient(app)
    assert other.post("/api/auth/login", json={"email": email, "password": "candidate-pw-1", "role": "candidate"}).status_code == 200
    body = {"role": "candidate", "current_password": "wrong-one", "new_password": "fresh-password-9"}
    assert here.post("/api/auth/change-password", json=body).status_code == 400
    assert here.post("/api/auth/change-password", json={**body, "role": "hr", "current_password": "candidate-pw-1"}).status_code == 401
    r = here.post("/api/auth/change-password", json={**body, "current_password": "candidate-pw-1"})
    assert r.status_code == 200, r.text
    assert here.get("/api/portal/me").status_code == 200   # this browser stays signed in
    assert other.get("/api/portal/me").status_code == 401  # other devices are signed out
    assert TestClient(app).post("/api/auth/login", json={"email": email, "password": "fresh-password-9", "role": "candidate"}).status_code == 200


def test_candidate_can_delete_own_account(client):
    from app.database import UPLOAD_DIR

    email = "leaving@example.com"
    me = candidate_client(email)
    me.post("/api/portal/resume", files={"file": ("bye.pdf", make_pdf(
        ["Leaving Soon", email, "Skills", "Python, Docker", "Education", "B.Tech in IT, 2019"]), "application/pdf")})
    job = client.post("/api/jobs", json={**JOB, "title": "Delete Test Job"}).json()["id"]
    me.post(f"/api/portal/apply/{job}", json=CONSENT)
    cand = client.get("/api/candidates", params={"search": email}).json()[0]
    stored = client.get(f"/api/candidates/{cand['id']}").json()
    files_before = set(UPLOAD_DIR.iterdir())

    assert me.post("/api/portal/delete-account", json={"password": "nope"}).status_code == 400
    assert me.post("/api/portal/delete-account", json={"password": "candidate-pw-1"}).status_code == 204
    assert client.get(f"/api/candidates/{cand['id']}").status_code == 404
    assert not [a for a in client.get("/api/applications").json() if a["candidate_email"] == email]
    assert len(set(UPLOAD_DIR.iterdir())) == len(files_before) - 1  # resume file removed
    assert me.get("/api/portal/me").status_code == 401
    assert TestClient(app).post("/api/auth/login", json={"email": email, "password": "candidate-pw-1", "role": "candidate"}).status_code == 401
    assert stored["resume_filename"] == "bye.pdf"


def test_reset_codes_are_limited_per_email_across_ips(client, monkeypatch):
    import app.auth as auth_mod

    monkeypatch.setattr(auth_mod, "send_email", lambda *a, **k: True)
    monkeypatch.setattr(auth_mod, "RESEND_SECONDS", 0)
    email = "many.ips@example.com"
    for i in range(auth_mod.MAX_REQUESTS):
        auth_mod._REQUESTS.pop(f"ip:10.0.0.{i}", None)
    codes = []
    for i in range(auth_mod.MAX_REQUESTS + 1):
        # simulate a different IP each time by clearing the per-IP counter for the test client
        auth_mod._REQUESTS.pop("ip:testclient", None)
        codes.append(TestClient(app).post("/api/auth/forgot-password", json={"email": email, "role": "candidate"}).status_code)
    assert codes[:-1] == [200] * auth_mod.MAX_REQUESTS and codes[-1] == 429


def test_limiter_memory_is_bounded(monkeypatch):
    import time as _t

    import app.auth as auth_mod

    monkeypatch.setattr(auth_mod, "MAX_TRACKED_KEYS", 50)
    store = auth_mod.defaultdict(auth_mod.deque)
    for i in range(200):
        store[f"old{i}"].append(_t.time() - 10_000)
    auth_mod._recent(store, "new", 60)
    assert len(store) <= 2
