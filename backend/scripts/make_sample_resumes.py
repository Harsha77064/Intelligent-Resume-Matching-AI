"""Generate 10 sample resumes in popular web-template styles (all people are fictional).

    cd backend
    .\\.venv\\Scripts\\python scripts\\make_sample_resumes.py

Writes PDFs to backend/sample_resumes/. Layout styles (original designs inspired by
common resume-template layouts): classic, sidebar, banner, label-column, timeline, skill-bars.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

OUT = Path(__file__).resolve().parents[1] / "sample_resumes"
W, H = A4
M = 40  # page margin

# ----------------------------------------------------------------------------- people
PEOPLE = [
    dict(
        file="01_Aarav_Nair_Python_Backend", style="classic", accent="#1f2937",
        name="Aarav Nair", title="Backend Engineer (Python)", email="aarav.nair@example.com",
        phone="+91 98450 11223", location="Bengaluru, India", link="linkedin.com/in/aarav-nair-dev",
        summary="Backend engineer with 6 years of experience designing REST APIs and microservices in Python. "
                "Comfortable owning services end to end, from schema design to Docker-based deployment on AWS.",
        skills={"Languages": "Python, SQL, Bash", "Frameworks": "FastAPI, Django, Celery, SQLAlchemy",
                "Data": "MySQL, PostgreSQL, Redis", "DevOps": "Docker, Kubernetes, AWS, GitHub Actions, Git"},
        experience=[
            ("Senior Software Engineer", "Finlytics Pvt Ltd, Bengaluru", "Mar 2023 - Present",
             ["Designed FastAPI microservices handling 2M requests/day with MySQL and Redis caching.",
              "Cut p95 latency by 38% by moving heavy reports to Celery workers.",
              "Containerised 9 services with Docker and moved deployments to Kubernetes on AWS."]),
            ("Software Engineer", "Orbit Soft Solutions, Pune", "Jul 2020 - Feb 2023",
             ["Built Django REST APIs for a logistics platform used by 300+ merchants.",
              "Introduced pytest and CI/CD pipelines, raising test coverage from 40% to 82%."]),
        ],
        education=[("B.Tech in Computer Science", "NIT Calicut", "2016 - 2020", "CGPA 8.4 / 10")],
        extras={"Certifications": ["AWS Certified Developer - Associate (2023)"]},
    ),
    dict(
        file="02_Diya_Kapoor_Frontend_React", style="sidebar", accent="#312e81",
        name="Diya Kapoor", title="Frontend Developer", email="diya.kapoor@example.com",
        phone="+91 99001 45678", location="Remote / Mumbai", link="github.com/diyakapoor",
        summary="Frontend developer who turns Figma designs into fast, accessible React applications. "
                "5 years of experience across design systems, dashboards and e-commerce.",
        skills={"Core": "React, TypeScript, JavaScript, HTML, CSS", "Styling": "Tailwind CSS, Sass, Material UI",
                "State & Data": "Redux, React Query, REST API, GraphQL", "Tooling": "Vite, Jest, Cypress, Git, Figma"},
        experience=[
            ("Frontend Engineer", "Pixelcraft Studio", "06/2022 - Present",
             ["Built a React + TypeScript design system with 60+ components used by 4 product teams.",
              "Improved Lighthouse accessibility score from 71 to 98 (WCAG 2.1 AA)."]),
            ("Junior Web Developer", "Shopnest", "07/2021 - 05/2022",
             ["Developed storefront pages with React, Redux and Tailwind CSS.",
              "Wrote Jest and Cypress tests for checkout flows."]),
        ],
        education=[("B.E in Information Technology", "Mumbai University", "2017 - 2021", "First Class with Distinction")],
        extras={"Languages": ["English (fluent)", "Hindi (native)"]},
    ),
    dict(
        file="03_Kabir_Sethi_Data_Analyst", style="banner", accent="#0f766e",
        name="Kabir Sethi", title="Data Analyst", email="kabir.sethi@example.com",
        phone="+91 98111 23456", location="Hyderabad, India", link="kabirsethi.github.io",
        summary="Data analyst with 4.5 years of experience turning messy business data into clear dashboards "
                "and decisions. Strong in SQL, Python (Pandas) and Power BI.",
        skills={"Analysis": "SQL, Python, Pandas, NumPy, Statistics, A/B testing",
                "BI": "Power BI, Tableau, Excel (pivot tables, VLOOKUP)", "Other": "Data Visualization, ETL, Google Sheets"},
        experience=[
            ("Data Analyst", "RetailIQ Analytics", "Jan 2023 - Present",
             ["Built 14 Power BI dashboards tracking sales, inventory and churn for 120 stores.",
              "Automated weekly Excel reporting with Python and SQL, saving 10 hours per week."]),
            ("Business Analyst Intern", "Quanta Consulting", "Jun 2022 - Dec 2022",
             ["Cleaned and analysed survey data in Pandas; presented findings to client leadership."]),
        ],
        education=[("M.Sc in Statistics", "University of Hyderabad", "2020 - 2022", ""),
                   ("B.Sc in Mathematics", "St. Joseph's College", "2017 - 2020", "")],
        extras={"Certifications": ["Microsoft PL-300: Power BI Data Analyst", "Google Data Analytics Certificate"]},
    ),
    dict(
        file="04_Meher_Ali_DevOps", style="labels", accent="#9a3412",
        name="Meher Ali", title="DevOps / Cloud Engineer", email="meher.ali@example.com",
        phone="+91 97000 55667", location="Chennai, India", link="linkedin.com/in/meher-ali",
        summary="DevOps engineer with 7+ years of experience automating infrastructure and CI/CD for "
                "Kubernetes-based platforms on AWS and Azure.",
        skills={"Cloud": "AWS (EC2, S3, EKS), Azure", "Containers": "Docker, Kubernetes, Helm",
                "IaC & CI/CD": "Terraform, Ansible, Jenkins, GitHub Actions", "Monitoring": "Prometheus, Grafana",
                "Scripting": "Python, Bash, Linux"},
        experience=[
            ("Lead DevOps Engineer", "CloudNine Systems", "Aug 2022 - Present",
             ["Migrated 40 services to EKS with Helm charts and Terraform modules.",
              "Reduced deployment time from 45 to 8 minutes with GitHub Actions pipelines."]),
            ("DevOps Engineer", "Netlink Technologies", "Jun 2019 - Jul 2022",
             ["Managed Jenkins CI/CD for 25 repositories; wrote Ansible playbooks for Linux servers.",
              "Set up Prometheus and Grafana monitoring with on-call alerting."]),
        ],
        education=[("B.Tech in Electronics and Communication", "Anna University", "2015 - 2019", "")],
        extras={"Certifications": ["Certified Kubernetes Administrator (CKA)", "HashiCorp Terraform Associate"]},
    ),
    dict(
        file="05_Ira_Menon_ML_Engineer", style="timeline", accent="#7c3aed",
        name="Ira Menon", title="Machine Learning Engineer", email="ira.menon@example.com",
        phone="+91 90080 33445", location="Bengaluru, India", link="github.com/iramenon",
        summary="ML engineer building NLP and LLM-powered features. Experienced with PyTorch, Hugging Face and "
                "production MLOps; enjoys taking models from notebook to API.",
        skills={"ML": "Machine Learning, Deep Learning, NLP, PyTorch, TensorFlow, Scikit-learn",
                "LLM": "LangChain, RAG, Hugging Face, Prompt Engineering", "Engineering": "Python, FastAPI, Docker, MLflow, SQL"},
        experience=[
            ("Machine Learning Engineer", "VisionAI Labs", "Sept 2022 - Present",
             ["Shipped a RAG-based support assistant with LangChain and FastAPI, deflecting 30% of tickets.",
              "Fine-tuned Hugging Face transformer models for intent classification (F1 0.91)."]),
            ("Data Science Intern", "Medisense", "Jan 2022 - Aug 2022",
             ["Built Scikit-learn and XGBoost risk models; tracked experiments in MLflow."]),
        ],
        education=[("M.Tech in Artificial Intelligence", "IIIT Hyderabad", "2020 - 2022", "Thesis: low-resource NER"),
                   ("B.Tech in Computer Science", "CUSAT", "2016 - 2020", "")],
        extras={"Publications": ["Few-shot NER for Indian languages, workshop paper (2022)"]},
    ),
    dict(
        file="06_Rohit_Bansal_Fresher_Python", style="classic", accent="#1d4ed8",
        name="Rohit Bansal", title="Graduate Software Engineer", email="rohit.bansal@example.com",
        phone="+91 95555 78901", location="Jaipur, India", link="github.com/rohitbansal",
        summary="Final-year computer science student looking for a backend developer role. Built several "
                "Python and FastAPI projects and completed a 6-month internship.",
        skills={"Languages": "Python, Java, C++, SQL", "Web": "FastAPI, Flask, HTML, CSS, REST API",
                "Tools": "Git, GitHub, Docker, MySQL, Postman", "CS": "Data Structures, Algorithms, OOP, DBMS"},
        experience=[
            ("Software Development Intern", "Brightpath Tech", "Jan 2025 - Jun 2025",
             ["Built REST API endpoints in FastAPI with MySQL for an internal HR tool.",
              "Wrote unit tests with pytest and fixed 20+ bugs reported by QA."]),
        ],
        projects=[("Expense Tracker API", "FastAPI, SQLite, JWT auth, Docker; deployed on Render."),
                  ("Campus Event Portal", "Flask + MySQL web app used by 1,200 students.")],
        education=[("B.Tech in Computer Science and Engineering", "JECRC University", "2021 - 2025", "CGPA 8.9 / 10"),
                   ("Class XII (CBSE)", "Delhi Public School, Jaipur", "2021", "92%")],
        extras={"Achievements": ["Top 5% in college coding contest (2024)", "Smart India Hackathon finalist"]},
    ),
    dict(
        file="07_Sana_Qureshi_Fullstack", style="bars", accent="#be185d",
        name="Sana Qureshi", title="Full Stack Developer (MERN)", email="sana.qureshi@example.com",
        phone="+91 98200 99887", location="Delhi NCR", link="sanaqureshi.dev",
        summary="Full stack developer with 5.5 years of experience shipping MERN and Next.js products, from "
                "database design to polished UI.",
        skills={"bars": [("JavaScript", 95), ("React", 90), ("Node.js", 85), ("Next.js", 80), ("MongoDB", 80),
                         ("TypeScript", 75), ("Express", 85), ("Docker", 60)],
                "Also": "REST API, GraphQL, Redux, Tailwind CSS, Jest, Git, AWS"},
        experience=[
            ("Full Stack Developer", "Shopnest Commerce", "May 2022 - Present",
             ["Rebuilt the storefront in Next.js, improving conversion by 12%.",
              "Built Node.js / Express order services on MongoDB with Redis queues."]),
            ("Associate Developer", "Webwise Agency", "Jun 2021 - Apr 2022",
             ["Delivered 15 client websites with React and Express; set up CI with GitHub Actions."]),
        ],
        education=[("BCA", "Jamia Millia Islamia", "2018 - 2021", ""), ("MCA", "IGNOU (distance)", "2021 - 2023", "")],
        extras={"Languages": ["English", "Hindi", "Urdu"]},
    ),
    dict(
        file="08_Vivek_Raman_Senior_Backend_Java", style="sidebar", accent="#14532d",
        name="Vivek Raman", title="Senior Backend Engineer (Java)", email="vivek.raman@example.com",
        phone="+91 98840 12121", location="Chennai, India", link="linkedin.com/in/vivekraman",
        summary="Senior backend engineer with 10+ years of experience building high-throughput payment systems "
                "with Java, Spring Boot and Kafka. Mentor to junior engineers.",
        skills={"Backend": "Java, Spring Boot, Hibernate, Microservices, REST API, gRPC",
                "Data": "PostgreSQL, Oracle DB, Redis, Kafka", "Cloud": "AWS, Docker, Kubernetes, Jenkins",
                "Practices": "System Design, Agile, JUnit"},
        experience=[
            ("Senior Software Engineer", "PayFlow Technologies", "2021 - Present",
             ["Lead engineer for payments ledger processing 5M transactions/day on Kafka + PostgreSQL.",
              "Designed idempotent Spring Boot microservices; mentored a team of 6."]),
            ("Software Engineer", "Infosys", "2016 - 2021",
             ["Built Java and Spring REST services for a banking client; migrated Oracle reports to PostgreSQL."]),
        ],
        education=[("B.E in Computer Science", "PSG College of Technology", "2012 - 2016", "")],
        extras={"Certifications": ["Oracle Certified Professional, Java SE 11"]},
    ),
    dict(
        file="09_Tara_Fernandes_QA_Automation", style="labels", accent="#0369a1",
        name="Tara Fernandes", title="QA Automation Engineer", email="tara.fernandes@example.com",
        phone="+91 93210 44556", location="Goa, India", link="linkedin.com/in/tarafernandes",
        summary="QA engineer with 6 years of experience in manual and automation testing for web and APIs.",
        skills={"Automation": "Selenium, Playwright, Cypress, Pytest", "API": "Postman, API Testing, REST API",
                "Languages": "Python, JavaScript, SQL", "Process": "Agile, JIRA, CI/CD, Manual Testing"},
        experience=[
            ("QA Automation Engineer", "Testify Labs", "Apr 2022 - Present",
             ["Built a Playwright + Pytest framework covering 600 regression cases, run in CI/CD.",
              "Reduced release regression time from 3 days to 4 hours."]),
            ("QA Engineer", "Nimbus Software", "Jul 2020 - Mar 2022",
             ["Manual and Selenium testing for a SaaS HR product; logged and triaged bugs in JIRA."]),
        ],
        education=[("B.Sc in Computer Science", "Goa University", "2017 - 2020", "")],
        extras={"Certifications": ["ISTQB Certified Tester Foundation Level"]},
    ),
    dict(
        file="10_Nikhil_Joshi_Data_Engineer", style="timeline", accent="#b45309",
        name="Nikhil Joshi", title="Data Engineer", email="nikhil.joshi@example.com",
        phone="+91 99876 54321", location="Pune, India", link="github.com/nikhiljoshi-de",
        summary="Data engineer with 5 years of experience building batch and streaming pipelines with Spark, "
                "Airflow and Snowflake.",
        skills={"Pipelines": "Spark, PySpark, Airflow, dbt, Kafka, ETL", "Warehouses": "Snowflake, BigQuery, Redshift",
                "Languages": "Python, SQL, Scala", "Cloud": "AWS, Databricks, Docker"},
        experience=[
            ("Data Engineer", "StreamCart", "Feb 2023 - Present",
             ["Built Airflow + dbt pipelines loading 2 TB/day into Snowflake.",
              "Moved clickstream processing to Spark Structured Streaming on Kafka."]),
            ("Associate Data Engineer", "Analytix Hub", "Aug 2021 - Jan 2023",
             ["Wrote PySpark ETL jobs on Databricks; optimised queries to cut costs by 25%."]),
        ],
        education=[("B.Tech in Information Technology", "Pune Institute of Computer Technology", "2017 - 2021", "")],
        extras={"Certifications": ["Snowflake SnowPro Core", "Databricks Data Engineer Associate"]},
    ),
]


# ----------------------------------------------------------------------------- drawing helpers
class Pen:
    def __init__(self, c: Canvas, x: float, y: float, width: float):
        self.c, self.x, self.y, self.w = c, x, y, width

    def text(self, s, size=9.5, font="Helvetica", color="#222222", gap=3, indent=0, leading=None):
        leading = leading or size * 1.32
        self.c.setFillColor(HexColor(color))
        self.c.setFont(font, size)
        for line in simpleSplit(s, font, size, self.w - indent):
            self.c.drawString(self.x + indent, self.y, line)
            self.y -= leading
        self.y -= gap

    def bullets(self, items, size=9.2, color="#333333"):
        for b in items:
            self.c.setFillColor(HexColor(color))
            self.c.setFont("Helvetica", size)
            self.c.drawString(self.x + 2, self.y, "•")
            self.text(b, size=size, color=color, indent=11, gap=1)
        self.y -= 3

    def heading(self, s, accent, rule=True, size=11, color=None):
        self.y -= 4
        self.c.setFillColor(HexColor(color or accent))
        self.c.setFont("Helvetica-Bold", size)
        self.c.drawString(self.x, self.y, s.upper())
        self.y -= 5
        if rule:
            self.c.setStrokeColor(HexColor(accent))
            self.c.setLineWidth(0.8)
            self.c.line(self.x, self.y, self.x + self.w, self.y)
        self.y -= 11

    def row(self, left, right, size=10, font="Helvetica-Bold", color="#111111", rcolor="#555555"):
        self.c.setFillColor(HexColor(color))
        self.c.setFont(font, size)
        self.c.drawString(self.x, self.y, left)
        self.c.setFillColor(HexColor(rcolor))
        self.c.setFont("Helvetica", size - 1)
        self.c.drawRightString(self.x + self.w, self.y, right)
        self.y -= size * 1.35


def contact_line(p):
    return f"{p['email']}  |  {p['phone']}  |  {p['location']}  |  {p['link']}"


def skill_lines(p):
    return [(k, v) for k, v in p["skills"].items() if k != "bars"]


def main_sections(pen: Pen, p, accent, with_skills=True, with_edu=True):
    pen.heading("Professional Summary" if p["experience"] else "Summary", accent)
    pen.text(p["summary"], size=9.6)
    if with_skills:
        pen.heading("Technical Skills", accent)
        for k, v in skill_lines(p):
            pen.text(f"{k}: {v}", size=9.4, gap=1)
        pen.y -= 3
    pen.heading("Work Experience", accent)
    for role, org, dates, bullets in p["experience"]:
        pen.row(role, dates)
        pen.text(org, size=9.2, font="Helvetica-Oblique", color="#555555", gap=2)
        pen.bullets(bullets)
    if p.get("projects"):
        pen.heading("Projects", accent)
        for t, d in p["projects"]:
            pen.text(t, size=9.6, font="Helvetica-Bold", gap=0)
            pen.text(d, size=9.2, color="#444444")
    if with_edu:
        pen.heading("Education", accent)
        for deg, school, dates, note in p["education"]:
            pen.row(deg, dates, size=9.8)
            pen.text(school + (f"  -  {note}" if note else ""), size=9.2, color="#555555", gap=4)
    for title, items in p["extras"].items():
        pen.heading(title, accent)
        pen.bullets(items)


# ----------------------------------------------------------------------------- templates
def classic(c: Canvas, p):
    a = p["accent"]
    c.setFillColor(HexColor(a))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(W / 2, H - 55, p["name"])
    c.setFont("Helvetica", 11)
    c.setFillColor(HexColor("#444444"))
    c.drawCentredString(W / 2, H - 72, p["title"])
    c.setFont("Helvetica", 8.8)
    c.drawCentredString(W / 2, H - 88, contact_line(p))
    pen = Pen(c, M, H - 112, W - 2 * M)
    main_sections(pen, p, a)


def banner(c: Canvas, p):
    a = p["accent"]
    c.setFillColor(HexColor(a))
    c.rect(0, H - 110, W, 110, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(M, H - 52, p["name"])
    c.setFont("Helvetica", 12)
    c.drawString(M, H - 72, p["title"])
    c.setFont("Helvetica", 8.8)
    c.drawString(M, H - 92, contact_line(p))
    pen = Pen(c, M, H - 135, W - 2 * M)
    main_sections(pen, p, a)


def sidebar(c: Canvas, p):
    a = p["accent"]
    sw = 190
    c.setFillColor(HexColor(a))
    c.rect(0, 0, sw, H, stroke=0, fill=1)
    side = Pen(c, 22, H - 55, sw - 40)
    side.text(p["name"], size=19, font="Helvetica-Bold", color="#ffffff", gap=2, leading=22)
    side.text(p["title"], size=10.5, color="#e0e7ff", gap=12)
    side.heading("Contact", "#ffffff", rule=False, size=10, color="#ffffff")
    for v in (p["email"], p["phone"], p["location"], p["link"]):
        side.text(v, size=8.6, color="#f1f5f9", gap=2)
    side.y -= 6
    side.heading("Skills", "#ffffff", rule=False, size=10, color="#ffffff")
    for k, v in skill_lines(p):
        side.text(k, size=8.8, font="Helvetica-Bold", color="#ffffff", gap=0)
        side.text(v, size=8.6, color="#f1f5f9", gap=5)
    side.heading("Education", "#ffffff", rule=False, size=10, color="#ffffff")
    for deg, school, dates, note in p["education"]:
        side.text(deg, size=8.8, font="Helvetica-Bold", color="#ffffff", gap=0)
        side.text(f"{school}, {dates}", size=8.4, color="#f1f5f9", gap=5)
    main = Pen(c, sw + 28, H - 55, W - sw - 28 - M)
    main_sections(main, p, a, with_skills=False, with_edu=False)


def labels(c: Canvas, p):
    a = p["accent"]
    c.setFont("Helvetica-Bold", 23)
    c.setFillColor(HexColor("#111111"))
    c.drawString(M, H - 58, p["name"])
    c.setFont("Helvetica", 11.5)
    c.setFillColor(HexColor(a))
    c.drawString(M, H - 76, p["title"])
    c.setFont("Helvetica", 8.8)
    c.setFillColor(HexColor("#555555"))
    c.drawString(M, H - 92, contact_line(p))
    c.setStrokeColor(HexColor(a))
    c.setLineWidth(2)
    c.line(M, H - 102, W - M, H - 102)
    lw = 110
    y = H - 125
    content_x = M + lw

    def section(title, draw):
        nonlocal y
        c.setFillColor(HexColor(a))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(M, y, title.upper())
        pen = Pen(c, content_x, y, W - content_x - M)
        draw(pen)
        y = pen.y - 8

    section("Profile", lambda pen: pen.text(p["summary"], size=9.5))
    section("Skills", lambda pen: [pen.text(f"{k}: {v}", size=9.3, gap=1) for k, v in skill_lines(p)])

    def exp(pen):
        for role, org, dates, bullets in p["experience"]:
            pen.row(role, dates, size=9.8)
            pen.text(org, size=9, font="Helvetica-Oblique", color="#555555", gap=2)
            pen.bullets(bullets, size=9)
    section("Experience", exp)
    section("Education", lambda pen: [pen.text(f"{d}, {s} ({dt})", size=9.3, gap=2) for d, s, dt, _ in p["education"]])
    for title, items in p["extras"].items():
        section(title, lambda pen, items=items: pen.bullets(items, size=9))


def timeline(c: Canvas, p):
    a = p["accent"]
    c.setFillColor(HexColor(a))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(M, H - 55, p["name"])
    c.setFillColor(HexColor("#333333"))
    c.setFont("Helvetica", 11)
    c.drawString(M, H - 72, p["title"])
    c.setFont("Helvetica", 8.8)
    c.drawString(M, H - 88, contact_line(p))
    pen = Pen(c, M, H - 110, W - 2 * M)
    pen.heading("About", a)
    pen.text(p["summary"], size=9.5)
    pen.heading("Skills", a)
    for k, v in skill_lines(p):
        pen.text(f"{k}: {v}", size=9.3, gap=1)
    pen.y -= 3
    gx = M + 112  # timeline gutter

    def entries(title, rows):
        pen.heading(title, a)
        for when, head, sub, bullets in rows:
            c.setFillColor(HexColor(a))
            c.circle(gx - 10, pen.y + 3, 3, stroke=0, fill=1)
            c.setFont("Helvetica-Bold", 8.6)
            c.drawString(M, pen.y, when)
            inner = Pen(c, gx, pen.y, W - gx - M)
            inner.text(head, size=9.8, font="Helvetica-Bold", gap=0)
            inner.text(sub, size=9, font="Helvetica-Oblique", color="#555555", gap=2)
            if bullets:
                inner.bullets(bullets, size=9)
            pen.y = inner.y - 4

    entries("Experience", [(d, r, o, b) for r, o, d, b in p["experience"]])
    entries("Education", [(dt, deg, sch + (f" - {n}" if n else ""), []) for deg, sch, dt, n in p["education"]])
    for title, items in p["extras"].items():
        pen.heading(title, a)
        pen.bullets(items, size=9)


def bars(c: Canvas, p):
    a = p["accent"]
    rw = 175
    rx = W - rw
    c.setFillColor(HexColor("#fdf2f8"))
    c.rect(rx, 0, rw, H, stroke=0, fill=1)
    c.setFillColor(HexColor(a))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(M, H - 55, p["name"])
    c.setFillColor(HexColor("#444444"))
    c.setFont("Helvetica", 11)
    c.drawString(M, H - 72, p["title"])
    main = Pen(c, M, H - 98, rx - M - 25)
    main_sections(main, p, a, with_skills=False)
    side = Pen(c, rx + 18, H - 55, rw - 36)
    side.heading("Contact", a, rule=False, size=10)
    for v in (p["email"], p["phone"], p["location"], p["link"]):
        side.text(v, size=8.4, color="#333333", gap=2)
    side.y -= 6
    side.heading("Skills", a, rule=False, size=10)
    for name, lvl in p["skills"]["bars"]:
        side.text(name, size=8.8, gap=1)
        c.setFillColor(HexColor("#f5d0e6"))
        c.roundRect(side.x, side.y + 4, side.w, 4, 2, stroke=0, fill=1)
        c.setFillColor(HexColor(a))
        c.roundRect(side.x, side.y + 4, side.w * lvl / 100, 4, 2, stroke=0, fill=1)
        side.y -= 8
    side.y -= 4
    side.heading("Also", a, rule=False, size=10)
    side.text(p["skills"]["Also"], size=8.6, color="#333333")


STYLES = {"classic": classic, "banner": banner, "sidebar": sidebar, "labels": labels, "timeline": timeline, "bars": bars}


def build(p) -> Path:
    path = OUT / f"{p['file']}.pdf"
    c = Canvas(str(path), pagesize=A4)
    c.setTitle(f"{p['name']} - Resume")
    c.setAuthor(p["name"])
    STYLES[p["style"]](c, p)
    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for person in PEOPLE:
        print("wrote", build(person).name)
