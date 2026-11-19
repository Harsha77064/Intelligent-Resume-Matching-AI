"""Skill dictionary used for resume parsing and job/resume skill normalisation.

Each row:  Canonical | Category | case-insensitive aliases | case-sensitive aliases
  * The canonical name is always a case-insensitive alias too, unless the
    insensitive-alias column starts with "!" (used for skills whose name is an
    everyday English word: "Excel", "Express", "Swift", "Spark", ...). Those only
    match with the exact capitalisation given in the last column.
Matching uses token boundaries so that "Java" does not match "JavaScript",
"SQL" does not match "MySQL" and "js" does not match inside "Next.js".
"""
from __future__ import annotations

import re
from functools import lru_cache

_TABLE = """
# ---------------------------------------------------------------- languages
Python | Language | python3, py3 |
Java | Language | core java, java 8, java 11, java 17 |
JavaScript | Language | js, es6, ecmascript, vanilla js |
TypeScript | Language | ts |
C | Language | ! c language, c programming, ansi c | ~C
C++ | Language | cpp |
C# | Language | csharp, c sharp |
Go | Language | ! golang, go lang | ~Go, GoLang
Rust | Language | ! rust lang | Rust
Kotlin | Language | |
Swift | Language | ! swiftui | Swift, SwiftUI
Objective-C | Language | objective c, objc |
PHP | Language | |
Ruby | Language | ! | Ruby
Scala | Language | |
R | Language | ! r programming, rstudio, r language | ~R
MATLAB | Language | |
Dart | Language | ! | Dart
Perl | Language | |
Bash | DevOps | shell scripting, shell script, bash scripting |
PowerShell | DevOps | |
SQL | Database | t-sql, tsql, pl/sql, plsql, sql queries |
NoSQL | Database | |
HTML | Frontend | html5 |
CSS | Frontend | css3 |
Sass | Frontend | scss |
# ---------------------------------------------------------------- backend
FastAPI | Backend | fast api |
Django | Backend | django rest framework, drf |
Flask | Backend | |
Node.js | Backend | nodejs, node js |
Express | Backend | ! express.js, expressjs | Express
NestJS | Backend | nest.js, nest js |
Spring Boot | Backend | springboot, spring framework, spring mvc | Spring
Hibernate | Backend | jpa |
.NET | Backend | dotnet, asp.net, .net core, asp.net core |
Ruby on Rails | Backend | rails, ror |
Laravel | Backend | |
REST API | Backend | rest api, rest apis, restful, restful api, restful apis, rest services | REST
GraphQL | Backend | |
gRPC | Backend | grpc |
Microservices | Backend | microservice, microservices architecture |
WebSockets | Backend | websocket, socket.io |
Celery | Backend | |
SQLAlchemy | Backend | |
Pydantic | Backend | |
Prisma | Backend | prisma orm |
OAuth | Backend | oauth2, oauth 2.0 |
JWT | Backend | json web token, json web tokens |
Kafka | Backend | apache kafka |
RabbitMQ | Backend | rabbit mq |
Nginx | DevOps | |
# ---------------------------------------------------------------- frontend
React | Frontend | react.js, reactjs, react js, react hooks |
Next.js | Frontend | nextjs, next js |
Angular | Frontend | angularjs, angular.js |
Vue.js | Frontend | vue, vuejs, vue js, vue 3 |
Nuxt.js | Frontend | nuxt, nuxtjs |
Svelte | Frontend | sveltekit |
Redux | Frontend | redux toolkit |
Tailwind CSS | Frontend | tailwind, tailwindcss |
Bootstrap | Frontend | |
Material UI | Frontend | mui, material-ui |
jQuery | Frontend | jquery |
Vite | Frontend | |
Webpack | Frontend | |
Responsive Design | Frontend | responsive web design |
Accessibility | Frontend | wcag, a11y, web accessibility |
Figma | Design | |
Adobe XD | Design | |
UI/UX | Design | ui/ux, ux design, ui design, user experience, user interface design |
# ---------------------------------------------------------------- mobile
Android | Mobile | android development, android sdk |
iOS | Mobile | ios development |
React Native | Mobile | |
Flutter | Mobile | |
Jetpack Compose | Mobile | |
# ---------------------------------------------------------------- databases
MySQL | Database | my sql |
PostgreSQL | Database | postgres, postgre sql, psql |
SQLite | Database | |
MongoDB | Database | mongo, mongoose |
Redis | Database | |
Cassandra | Database | apache cassandra |
DynamoDB | Database | dynamo db |
Elasticsearch | Database | elastic search, elk stack, opensearch |
Oracle | Database | ! oracle db, oracle database, oracle sql, oracle 19c | Oracle
SQL Server | Database | ms sql, mssql, microsoft sql server |
Firebase | Database | firestore |
Supabase | Database | |
Neo4j | Database | |
Snowflake | Data | |
BigQuery | Data | big query, google bigquery |
Redshift | Data | amazon redshift, aws redshift |
# ---------------------------------------------------------------- devops / cloud
Docker | DevOps | docker compose, docker-compose, dockerfile |
Kubernetes | DevOps | k8s, kubectl, eks, aks, gke |
Helm | DevOps | ! helm charts | Helm
Git | DevOps | version control |
GitHub | DevOps | |
GitLab | DevOps | |
Bitbucket | DevOps | |
CI/CD | DevOps | ci/cd, cicd, ci cd, continuous integration, continuous deployment, continuous delivery, ci/cd pipelines |
Jenkins | DevOps | |
GitHub Actions | DevOps | github action |
GitLab CI | DevOps | gitlab ci/cd |
Linux | DevOps | ubuntu, centos, debian, red hat, rhel, unix |
AWS | Cloud | amazon web services, aws lambda, amazon s3, aws s3, aws ec2, cloudformation | EC2, S3
Azure | Cloud | microsoft azure, azure devops |
GCP | Cloud | google cloud, google cloud platform |
Terraform | DevOps | |
Ansible | DevOps | |
Prometheus | DevOps | |
Grafana | DevOps | |
Serverless | Cloud | serverless framework |
Heroku | Cloud | |
Vercel | Cloud | |
Netlify | Cloud | |
# ---------------------------------------------------------------- data
Pandas | Data | |
NumPy | Data | numpy |
Matplotlib | Data | |
Seaborn | Data | |
Plotly | Data | |
Excel | Data | ! ms excel, microsoft excel, advanced excel, excel vba, vlookup, pivot tables, pivot table | Excel
Google Sheets | Data | |
Power BI | Data | powerbi, power-bi, dax |
Tableau | Data | |
Looker | Data | looker studio, google data studio |
Statistics | Data | statistical analysis, statistical modeling, hypothesis testing, a/b testing, probability |
Data Analysis | Data | data analytics, analyzing data, exploratory data analysis, eda |
Data Visualization | Data | data visualisation, dashboards, dashboarding |
Data Cleaning | Data | data wrangling, data preprocessing |
Spark | Data | ! pyspark, apache spark, spark sql | Spark
Hadoop | Data | hdfs, mapreduce |
Hive | Data | ! apache hive | Hive
Airflow | Data | apache airflow |
dbt | Data | data build tool |
Databricks | Data | |
ETL | Data | elt, data pipelines, data pipeline |
Data Warehousing | Data | data warehouse |
SAS | Data | ! | SAS
SPSS | Data | |
# ---------------------------------------------------------------- AI / ML
Machine Learning | AI | ml, machine-learning |
Deep Learning | AI | neural networks, neural network, cnn, rnn, lstm |
NLP | AI | natural language processing |
Computer Vision | AI | image processing |
Generative AI | AI | genai, gen ai, generative ai |
LLM | AI | llms, large language models, large language model, gpt, openai api, claude api |
RAG | AI | retrieval augmented generation, retrieval-augmented generation | RAG
Prompt Engineering | AI | |
LangChain | AI | lang chain |
LlamaIndex | AI | llama index |
Hugging Face | AI | huggingface, hugging face transformers |
Scikit-learn | AI | sklearn, scikit learn, scikit |
TensorFlow | AI | tensor flow |
Keras | AI | |
PyTorch | AI | torch |
XGBoost | AI | lightgbm |
OpenCV | AI | open cv |
spaCy | AI | spacy |
NLTK | AI | |
MLOps | AI | ml ops |
MLflow | AI | ml flow |
Time Series | AI | time series analysis, forecasting |
# ---------------------------------------------------------------- testing / QA
Pytest | Testing | py.test |
JUnit | Testing | |
Jest | Testing | |
Cypress | Testing | |
Playwright | Testing | |
Selenium | Testing | selenium webdriver |
Unit Testing | Testing | unit tests, unit test, tdd, test driven development |
Manual Testing | Testing | |
Automation Testing | Testing | test automation, automated testing |
API Testing | Testing | |
Postman | Testing | |
# ---------------------------------------------------------------- tools / practice
JIRA | Tools | jira |
Confluence | Tools | |
Swagger | Tools | openapi |
Agile | Practice | scrum, kanban, sprint planning |
System Design | Practice | low level design, high level design, lld, hld |
Data Structures | Practice | data structures and algorithms, dsa |
Algorithms | Practice | |
OOP | Practice | object oriented programming, object-oriented programming, oops, object oriented design |
Design Patterns | Practice | |
DBMS | Practice | database management systems |
Operating Systems | Practice | |
Computer Networks | Practice | networking, tcp/ip |
Cybersecurity | Security | cyber security, information security, network security |
OWASP | Security | |
Blockchain | Other | |
Solidity | Other | |
Unity | Other | ! unity3d | Unity
SEO | Marketing | search engine optimization |
Digital Marketing | Marketing | |
Salesforce | Business | |
SAP | Business | ! | SAP
Project Management | Business | |
# ---------------------------------------------------------------- soft skills
Communication | Soft | communication skills |
Leadership | Soft | team leadership |
Teamwork | Soft | team player, collaboration |
Problem Solving | Soft | problem-solving, analytical skills |
"""

# Owning one of these skills implies the parent skill (e.g. Django work is Python work).
IMPLIES: dict[str, list[str]] = {
    "Django": ["Python"], "Flask": ["Python"], "FastAPI": ["Python"], "Pandas": ["Python"],
    "NumPy": ["Python"], "Pytest": ["Python"], "PyTorch": ["Machine Learning"],
    "TensorFlow": ["Machine Learning"], "Keras": ["Deep Learning"], "Scikit-learn": ["Machine Learning"],
    "XGBoost": ["Machine Learning"], "Deep Learning": ["Machine Learning"],
    "Spring Boot": ["Java"], "Hibernate": ["Java"], "JUnit": ["Java"],
    "Express": ["Node.js"], "NestJS": ["Node.js", "TypeScript"], "Next.js": ["React"],
    "Redux": ["React"], "React Native": ["React"], "Nuxt.js": ["Vue.js"],
    "MySQL": ["SQL"], "PostgreSQL": ["SQL"], "SQL Server": ["SQL"], "SQLite": ["SQL"],
    "MongoDB": ["NoSQL"], "DynamoDB": ["NoSQL"], "Cassandra": ["NoSQL"],
    "GitHub": ["Git"], "GitLab": ["Git"], "Bitbucket": ["Git"],
    "Jenkins": ["CI/CD"], "GitHub Actions": ["CI/CD", "Git"], "GitLab CI": ["CI/CD", "Git"],
    "LangChain": ["LLM"], "LlamaIndex": ["LLM"], "RAG": ["LLM"], "Generative AI": ["LLM"],
    "Helm": ["Kubernetes"], "Laravel": ["PHP"], "Ruby on Rails": ["Ruby"], "Flutter": ["Dart"],
}


def _parse() -> dict[str, dict]:
    skills: dict[str, dict] = {}
    for raw in _TABLE.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, cat, ci, cs = (p.strip() for p in (line.split("|") + ["", ""])[:4])
        strict = ci.startswith("!")
        ci_list = [a.strip().lower() for a in ci.lstrip("!").split(",") if a.strip()]
        cs_list = [a.strip() for a in cs.split(",") if a.strip()]
        if not strict:
            ci_list.append(name.lower())
        skills[name] = {"cat": cat, "aliases": sorted(set(ci_list), key=len, reverse=True), "cs": cs_list}
    return skills


SKILLS: dict[str, dict] = _parse()

# A token boundary: not preceded/followed by a letter, digit, + or #. A "." directly
# before the alias also blocks it, so "js" in "Next.js" or "net" in "asp.net" is not
# matched on its own (aliases that start with "." handle that themselves).
_BOUND_L = r"(?<![A-Za-z0-9+#.])"
_BOUND_L_DOT = r"(?<![A-Za-z0-9+#])"
_BOUND_R = r"(?![A-Za-z0-9+#])"


# list context: start of line or after a separator, and followed by a separator/end
_LIST_L = r"(?:^|(?<=[,:;/|•·(])|(?<=[,:;/|•·(] ))"
_LIST_R = r"(?=\s*(?:[,;/|•·)]|$))"


def _alias_pattern(alias: str) -> str:
    if alias.startswith("~"):
        return _LIST_L + re.escape(alias[1:]) + _LIST_R
    parts = [re.escape(p) for p in alias.split()]
    left = _BOUND_L_DOT if alias.startswith(".") else _BOUND_L
    return left + r"\s+".join(parts) + _BOUND_R


@lru_cache(maxsize=1)
def _compiled() -> list[tuple[str, re.Pattern | None, re.Pattern | None]]:
    out = []
    for canonical, meta in SKILLS.items():
        ci = re.compile("|".join(_alias_pattern(a) for a in meta["aliases"]), re.IGNORECASE) if meta["aliases"] else None
        cs = re.compile("|".join(_alias_pattern(a) for a in meta["cs"]), re.MULTILINE) if meta["cs"] else None
        out.append((canonical, ci, cs))
    return out


@lru_cache(maxsize=1)
def _lookup() -> dict[str, str]:
    table: dict[str, str] = {}
    for canonical, meta in SKILLS.items():
        table[canonical.lower()] = canonical
        for a in meta["aliases"] + [c.lstrip("~").lower() for c in meta["cs"]]:
            table.setdefault(a.lower(), canonical)
    return table


def _search(ci: re.Pattern | None, cs: re.Pattern | None, text: str):
    hits = [m for m in ((ci.search(text) if ci else None), (cs.search(text) if cs else None)) if m]
    return min(hits, key=lambda m: m.start()) if hits else None


def extract_skills(text: str, with_implied: bool = True) -> list[str]:
    """Return canonical skills found in the text, ordered by first occurrence.

    Implied parent skills (Django -> Python) are appended after the explicit ones.
    """
    found: list[tuple[int, str]] = []
    for canonical, ci, cs in _compiled():
        m = _search(ci, cs, text)
        if m:
            found.append((m.start(), canonical))
    found.sort()
    skills = [s for _, s in found]
    if with_implied:
        have = set(skills)
        for s in list(skills):
            for parent in IMPLIES.get(s, []):
                if parent not in have:
                    have.add(parent)
                    skills.append(parent)
    return skills


def normalize_skill(name: str) -> str:
    """Map user-entered skill text to its canonical form when known."""
    cleaned = " ".join(name.strip().split())
    return _lookup().get(cleaned.lower(), cleaned)


def normalize_skills(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if not n or not n.strip():
            continue
        c = normalize_skill(n)
        if c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


def is_known(name: str) -> bool:
    return name.lower() in _lookup()


def text_has_skill(text: str, skill: str) -> bool:
    """Search free text for a (possibly custom, non-dictionary) skill."""
    canonical = normalize_skill(skill)
    for c, ci, cs in _compiled():
        if c == canonical:
            return bool(_search(ci, cs, text))
    return bool(re.search(_alias_pattern(skill.lower()), text, re.IGNORECASE))


def skill_category(skill: str) -> str:
    meta = SKILLS.get(normalize_skill(skill))
    return meta["cat"] if meta else "Other"


def all_skills() -> list[dict]:
    return [{"name": k, "category": v["cat"]} for k, v in sorted(SKILLS.items(), key=lambda kv: kv[0].lower())]
