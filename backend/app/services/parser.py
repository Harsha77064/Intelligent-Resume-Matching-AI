"""Resume parsing: PDF text extraction plus skills, education and experience.

Only job-related information is extracted. Protected or sensitive
characteristics (age, gender, caste, religion, disability, photo, marital
status, ...) are never parsed, stored or used in scoring.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date

from .skills import extract_skills


class ResumeParseError(ValueError):
    pass


# ---------------------------------------------------------------- PDF text

def extract_pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise ResumeParseError("File is not a valid PDF.")
    try:
        import pymupdf as fitz

        with fitz.open(stream=data, filetype="pdf") as doc:
            text = "\n".join(page.get_text("text") for page in doc)
    except ImportError:  # pragma: no cover - fallback when PyMuPDF missing
        from io import BytesIO

        from pypdf import PdfReader

        text = "\n".join((p.extract_text() or "") for p in PdfReader(BytesIO(data)).pages)
    except Exception as exc:  # corrupt / encrypted PDF
        raise ResumeParseError(f"Could not read PDF: {exc}") from exc
    text = text.replace(" ", " ").replace("–", "-").replace("—", "-")
    if len(text.strip()) < 30:
        raise ResumeParseError(
            "No readable text found in PDF (it may be a scanned image). Please upload a text-based PDF."
        )
    return text


# ---------------------------------------------------------------- contact

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")


def _guess_name(lines: list[str]) -> str | None:
    for line in lines[:6]:
        clean = line.strip()
        if not clean or EMAIL_RE.search(clean) or any(ch.isdigit() for ch in clean):
            continue
        words = clean.split()
        if 1 < len(words) <= 4 and all(w[:1].isupper() for w in words if w[:1].isalpha()):
            if clean.lower() not in {"curriculum vitae", "resume"}:
                return clean.title() if clean.isupper() else clean
    return None


# ---------------------------------------------------------------- education

# (regex, label, level) - level: 1 diploma, 2 bachelor, 3 master, 4 doctorate
DEGREES = [
    (r"\bph\.?\s?d\b|doctorate", "PhD", 4),
    (r"\bm\.?\s?tech\b|master of technology", "M.Tech", 3),
    (r"\bm\.?\s?sc\b|master of science", "M.Sc", 3),
    (r"\bmca\b|master of computer applications", "MCA", 3),
    (r"\bmba\b|master of business", "MBA", 3),
    (r"\bm\.\s?e\b|master of engineering", "M.E", 3),
    (r"\bmasters?\b", "Master's", 3),
    (r"\bb\.?\s?tech\b|bachelor of technology", "B.Tech", 2),
    (r"\bb\.\s?e\b|bachelor of engineering", "B.E", 2),
    (r"\bb\.?\s?sc\b|bachelor of science", "B.Sc", 2),
    (r"\bbca\b|bachelor of computer applications", "BCA", 2),
    (r"\bb\.?\s?com\b|bachelor of commerce", "B.Com", 2),
    (r"\bbachelors?\b|\bundergraduate\b", "Bachelor's", 2),
    (r"\bdiploma\b", "Diploma", 1),
]
DEGREE_RES = [(re.compile(rx, re.IGNORECASE), label, level) for rx, label, level in DEGREES]
LEVEL_NAMES = {0: "Any", 1: "Diploma", 2: "Bachelor's", 3: "Master's", 4: "PhD"}
FIELD_RE = re.compile(
    r"(computer science|information technology|electronics|electrical|mechanical|data science|"
    r"statistics|mathematics|software engineering|artificial intelligence|commerce|business)",
    re.IGNORECASE,
)


def extract_education(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        for rx, label, level in DEGREE_RES:
            if rx.search(line):
                if label in seen:
                    break
                seen.add(label)
                fld = FIELD_RE.search(line)
                years = re.findall(r"(?:19|20)\d{2}", line)
                results.append(
                    {
                        "degree": label,
                        "level": level,
                        "field": fld.group(1).title() if fld else None,
                        "year": int(years[-1]) if years else None,
                    }
                )
                break
    results.sort(key=lambda e: -e["level"])
    return results


def education_level(education: list[dict]) -> int:
    return max((e.get("level", 0) for e in education), default=0)


# ---------------------------------------------------------------- experience

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
EXPLICIT_EXP_RE = re.compile(
    r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:professional\s+|industry\s+|work\s+|hands[- ]on\s+)?experience",
    re.IGNORECASE,
)

# One date: "Jan 2021", "January, 2021", "06/2021", "6-2021", "06.2021" or "2021".
# A numeric month must not be glued to another digit or slash (so "2019-2021" is two years).
_MON_NAME = r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"


def _date(tag: str) -> str:
    return (
        rf"(?:(?P<{tag}m>(?:{_MON_NAME})[a-z]*\.?)\s*,?\s*|(?<![\d/.-])(?P<{tag}n>0?[1-9]|1[0-2])\s*[/.-]\s*)?"
        rf"(?P<{tag}y>(?:19|20)\d{{2}}|'\d{{2}})(?!\d)"
    )


_END_WORDS = r"present|current|currently|now|till\s+date|to\s+date|ongoing|today|date"
RANGE_RE = re.compile(
    _date("s") + r"\s*(?:-|to|till|until|through)\s*(?:(?P<present>" + _END_WORDS + r")\b|" + _date("e") + ")",
    re.IGNORECASE,
)
EXP_HEADERS = re.compile(
    r"^\s*(work\s+|professional\s+|relevant\s+|industry\s+)?(experience|employment(\s+history)?|work\s+history|"
    r"career(\s+history)?|internships?|internship\s+experience)\s*:?\s*$",
    re.I,
)
OTHER_HEADERS = re.compile(
    r"^\s*(education(al)?(\s+(details|qualifications?|background))?|academics?|academic\s+(details|background|qualifications?)|"
    r"qualifications?|skills|technical\s+skills|key\s+skills|core\s+competencies|projects|academic\s+projects|personal\s+projects|"
    r"certifications?|courses|achievements|awards|summary|profile|objective|career\s+objective|languages|interests|hobbies|"
    r"publications|declaration|references|extra[- ]?curricular|activities|volunteer(ing)?)\s*:?\s*$",
    re.I,
)
# Sections whose dates are NOT employment (study years, project dates, ...)
NON_WORK_HEADERS = re.compile(
    r"^\s*(education|academic|qualification|projects|personal projects|academic projects|certification|courses|achievements|"
    r"awards|publications|extra|activities|volunteer)",
    re.I,
)
ACADEMIC_LINE = re.compile(
    r"\b(university|college|institute|school|academy|cgpa|gpa|sgpa|percentage|marks|semester|class\s+(x|xii|10|12)|"
    r"ssc|hsc|cbse|icse|board|graduat|b\.?\s?tech|b\.?\s?e\b|b\.?\s?sc|m\.?\s?tech|m\.?\s?sc|mca|mba|bca|bachelor|master|diploma|ph\.?d)",
    re.I,
)


def _normalize_dashes(text: str) -> str:
    return (text.replace("–", "-").replace("—", "-").replace("‒", "-").replace("−", "-")
            .replace("’", "'").replace("‘", "'"))


def _sections(text: str) -> tuple[str, str]:
    """Split text into (experience-section text, text outside non-work sections)."""
    exp: list[str] = []
    general: list[str] = []
    mode = "general"  # general | exp | skip
    prev_academic = False
    for line in text.splitlines():
        stripped = line.strip()
        if EXP_HEADERS.match(stripped):
            mode = "exp"
            continue
        if len(stripped) < 45 and OTHER_HEADERS.match(stripped):
            mode = "skip" if NON_WORK_HEADERS.match(stripped) else "general"
            continue
        if mode == "exp":
            exp.append(line)
        elif mode == "general":
            # without headers, drop lines about studies and a date line right after them
            academic = bool(ACADEMIC_LINE.search(line))
            if not academic and not prev_academic:
                general.append(line)
            prev_academic = academic or (prev_academic and not stripped)
    return "\n".join(exp), "\n".join(general)


def _month(name: str | None, num: str | None, default: int) -> int:
    if name:
        return MONTHS.get(name[:3].lower(), default)
    if num:
        return int(num)
    return default


def _year(y: str) -> int:
    return 2000 + int(y[1:]) if y.startswith("'") else int(y)


def _ranges(text: str, today: date) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    now = today.year * 12 + today.month - 1
    for m in RANGE_RE.finditer(text):
        g = m.groupdict()
        start = _year(g["sy"]) * 12 + _month(g["sm"], g["sn"], 1) - 1
        if g["present"]:
            end = now
        else:
            end = _year(g["ey"]) * 12 + _month(g["em"], g["en"], 12) - 1
        end = min(end, now)
        if start <= end and (end - start) < 45 * 12 and start <= now:
            out.append((start, end))
    return out


def extract_experience_years(text: str, today: date | None = None) -> float:
    today = today or date.today()
    text = _normalize_dashes(text)
    explicit = [float(m.group(1)) for m in EXPLICIT_EXP_RE.finditer(text) if float(m.group(1)) <= 45]
    if explicit:
        return round(max(explicit), 1)

    exp_section, general = _sections(text)
    ranges = _ranges(exp_section, today) or _ranges(general, today)
    if not ranges:
        return 0.0
    # merge overlapping periods so parallel roles are not double counted
    ranges.sort()
    merged = [list(ranges[0])]
    for s, e in ranges[1:]:
        if s <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    months = sum(e - s + 1 for s, e in merged)
    return round(months / 12, 1)


# ---------------------------------------------------------------- facade

@dataclass
class ParsedResume:
    text: str
    name: str | None
    email: str | None
    phone: str | None
    skills: list[str] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    experience_years: float = 0.0
    parse_ms: float = 0.0


def parse_resume(data: bytes) -> ParsedResume:
    t0 = time.perf_counter()
    text = extract_pdf_text(data)
    lines = [l for l in text.splitlines() if l.strip()]
    email = EMAIL_RE.search(text)
    phone = next((m for m in PHONE_RE.finditer(text) if sum(c.isdigit() for c in m.group(1)) >= 10), None)
    parsed = ParsedResume(
        text=text,
        name=_guess_name(lines),
        email=email.group(0) if email else None,
        phone=" ".join(phone.group(1).split()) if phone else None,
        skills=extract_skills(text),
        education=extract_education(text),
        experience_years=extract_experience_years(text),
    )
    parsed.parse_ms = round((time.perf_counter() - t0) * 1000, 1)
    return parsed
