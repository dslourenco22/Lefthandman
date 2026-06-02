"""NLP utilities: contact extraction, skill normalization, section parsing,
years-of-experience estimation, and job-description structuring.

Uses spaCy where available for named-entity recognition (candidate name,
locations) and falls back to robust regex heuristics otherwise.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from functools import lru_cache

from ..config import settings

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# --- Regex patterns ---------------------------------------------------------
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{3}\)?[\s.\-]?)\d{3}[\s.\-]?\d{4})"
)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_/]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-_]+", re.I)
YEARS_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\+?\s*(?:years|yrs?)\b", re.I)
YEAR_RANGE_RE = re.compile(r"(19|20)\d{2}")

# Section headers commonly found in resumes.
SECTION_ALIASES = {
    "experience": ["experience", "work experience", "employment", "professional experience", "work history"],
    "education": ["education", "academic background", "academics"],
    "skills": ["skills", "technical skills", "core competencies", "technical competencies", "competencies"],
    "certifications": ["certifications", "certificates", "licenses", "certifications & licenses"],
    "projects": ["projects", "key projects", "selected projects"],
    "languages": ["languages"],
    "summary": ["summary", "professional summary", "profile", "objective", "about"],
}

# Vocabulary used to spot skills/certs/soft-skills inside free text.
KNOWN_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby", "php",
    "sql", "postgresql", "mysql", "microsoft sql server", "mongodb", "redis",
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring",
    "aws", "amazon web services", "microsoft azure", "google cloud platform",
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd", "git",
    "linux", "windows server", "tcp/ip", "rest api", "graphql",
    "machine learning", "natural language processing", "data analysis", "pandas",
    "tensorflow", "pytorch", "siem", "splunk", "wireshark", "nmap", "penetration testing",
    "information security", "incident response", "firewall", "vpn", "active directory",
    "help desk", "it support", "networking", "powershell", "bash", "excel", "tableau",
    "power bi", "agile", "scrum", "project management", "jira", "confluence",
    # Manufacturing / electro-mechanical / skilled trades
    "wire harness assembly", "cable assembly", "point-to-point wiring", "wiring",
    "electrical schematics", "schematics", "wire run lists", "blueprint reading",
    "control panel assembly", "mechanical assembly", "electro-mechanical assembly",
    "hand tools", "power tools", "crimping", "soldering", "torque tools",
    "testing and troubleshooting", "troubleshooting", "quality control",
    "work order documentation", "assembly", "fabrication", "machining", "cnc",
    "welding", "calibration", "preventive maintenance", "lean manufacturing",
    "5s", "six sigma", "iso 9001", "gd&t", "multimeter", "oscilloscope",
    # Purchasing / supply chain / operations
    "purchasing", "procurement", "sourcing", "vendor management", "supplier management",
    "supply chain", "inventory management", "negotiation", "contract management",
    "erp", "sap", "oracle", "netsuite", "mrp", "logistics", "cost analysis",
    "demand planning", "category management", "rfq", "purchase orders",
    # General business
    "customer service", "data entry", "scheduling", "budgeting", "forecasting",
    "accounting", "quickbooks", "microsoft office", "word", "outlook",
]
KNOWN_CERTS = [
    "comptia security+", "comptia network+", "comptia a+",
    "certified information systems security professional", "cissp",
    "certified ethical hacker", "ceh", "project management professional", "pmp",
    "aws certified solutions architect", "aws certified", "azure administrator",
    "microsoft certified", "cisco certified network associate", "ccna",
    "itil", "certified information security manager", "cism",
]
KNOWN_SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "collaboration", "problem solving",
    "problem-solving", "time management", "adaptability", "critical thinking",
    "attention to detail", "mentoring", "stakeholder management", "presentation",
]
DEGREE_TERMS = [
    "ph.d", "phd", "doctorate", "master", "m.s", "msc", "mba", "bachelor", "b.s",
    "bsc", "b.a", "associate", "diploma", "high school",
]


@lru_cache
def _aliases() -> dict[str, str]:
    """Return a flat alias->canonical map built from skill_aliases.json."""
    with open(os.path.join(_DATA_DIR, "skill_aliases.json")) as f:
        raw = json.load(f)
    flat: dict[str, str] = {}
    for canonical, variants in raw.items():
        flat[canonical.lower()] = canonical.lower()
        for v in variants:
            flat[v.lower()] = canonical.lower()
    return flat


@lru_cache
def _nlp():
    """Lazy-load spaCy. Returns None if the model is unavailable."""
    try:
        import spacy
        return spacy.load(settings.SPACY_MODEL)
    except Exception:
        return None


def normalize_skill(skill: str) -> str:
    """Map a raw skill string to its canonical form."""
    s = re.sub(r"\s+", " ", skill.strip().lower())
    s = s.strip(" .,:;")
    return _aliases().get(s, s)


def normalize_skill_list(skills: list[str]) -> list[str]:
    seen, out = set(), []
    for s in skills:
        c = normalize_skill(s)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


# --- Contact extraction -----------------------------------------------------
def extract_contact(text: str) -> dict:
    email = (EMAIL_RE.search(text) or [None])
    email = email.group(0) if email else ""
    phone_m = PHONE_RE.search(text)
    phone = phone_m.group(0).strip() if phone_m else ""
    linkedin_m = LINKEDIN_RE.search(text)
    github_m = GITHUB_RE.search(text)
    return {
        "email": email,
        "phone": phone,
        "linkedin": linkedin_m.group(0) if linkedin_m else "",
        "github": github_m.group(0) if github_m else "",
    }


def extract_name(text: str) -> str:
    """Best-effort candidate name: prefer a PERSON entity near the top,
    else the first non-empty line that isn't contact info / a header."""
    head = "\n".join(text.splitlines()[:8])
    nlp = _nlp()
    if nlp is not None:
        doc = nlp(head)
        for ent in doc.ents:
            if ent.label_ == "PERSON" and 1 <= len(ent.text.split()) <= 4:
                return ent.text.strip()
    for line in text.splitlines():
        line = line.strip()
        if not line or EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        low = line.lower()
        if any(h in low for headers in SECTION_ALIASES.values() for h in headers):
            continue
        if 1 <= len(line.split()) <= 4 and not any(ch.isdigit() for ch in line):
            return line
    return ""


def extract_location(text: str) -> str:
    nlp = _nlp()
    if nlp is None:
        return ""
    doc = nlp("\n".join(text.splitlines()[:10]))
    gpes = [e.text for e in doc.ents if e.label_ == "GPE"]
    return ", ".join(dict.fromkeys(gpes[:2])) if gpes else ""


# --- Section + content parsing ---------------------------------------------
def _split_sections(text: str) -> dict[str, str]:
    """Split resume text into labelled sections by header lines."""
    lines = text.splitlines()
    header_lookup = {}
    for key, names in SECTION_ALIASES.items():
        for n in names:
            header_lookup[n] = key

    sections: dict[str, list[str]] = {}
    current = "_preamble"
    sections[current] = []
    for line in lines:
        stripped = line.strip().lower().rstrip(":")
        if stripped in header_lookup and len(line.strip()) < 40:
            current = header_lookup[stripped]
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _find_terms(text: str, vocabulary: list[str]) -> list[str]:
    low = text.lower()
    found = []
    for term in vocabulary:
        # word-boundary-ish match that tolerates symbols like + and #
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(term) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, low):
            found.append(term)
    return found


def estimate_years_experience(text: str) -> float:
    """Estimate total years of experience.

    Prefers an explicit '<n> years' statement; otherwise infers from the span
    of 4-digit years mentioned in the experience section.
    """
    explicit = [float(m) for m in YEARS_RE.findall(text)]
    if explicit:
        return max(explicit)
    years = [int(m.group(0)) for m in YEAR_RANGE_RE.finditer(text)]
    if len(years) >= 2:
        span = max(years) - min(years)
        if 0 < span <= 50:
            return float(span)
    return 0.0


def parse_resume(text: str) -> dict:
    """Full structured parse of a resume's raw text."""
    contact = extract_contact(text)
    sections = _split_sections(text)
    skills_section = sections.get("skills", "")
    skills = _find_terms(skills_section + "\n" + text, KNOWN_SKILLS)
    # Also pull comma/bullet separated tokens from an explicit skills section
    # and keep those that normalize to a known skill.
    if skills_section:
        for token in re.split(r"[,\n•·|/]+", skills_section):
            token = token.strip()
            if 1 < len(token) <= 30:
                norm = normalize_skill(token)
                if norm in KNOWN_SKILLS:
                    skills.append(norm)

    certifications = _find_terms(text, KNOWN_CERTS)
    education = _extract_education(sections.get("education", "") or text)

    return {
        **contact,
        "name": extract_name(text),
        "location": extract_location(text),
        "summary": sections.get("summary", "")[:1500],
        "skills_raw": normalize_skill_list(skills),
        "certifications": normalize_skill_list(certifications),
        "education": education,
        "work_experience": _extract_experience_items(sections.get("experience", "")),
        "projects": _extract_bullets(sections.get("projects", "")),
        "languages": _extract_bullets(sections.get("languages", "")),
        "years_experience": estimate_years_experience(
            sections.get("experience", "") or text
        ),
    }


def _extract_education(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        low = line.lower()
        if any(term in low for term in DEGREE_TERMS):
            level = next((t for t in DEGREE_TERMS if t in low), "")
            out.append({"text": line.strip(), "level": level})
    return out[:6]


def _role_years(title_line: str) -> tuple[float, str]:
    """From a role's header line, return (duration_years, displayed_span).

    Handles '2018 - Present', '2020 - 2022', '(2019-2024)', etc. 'Present'/
    'Current' resolves to the current year. Returns (0.0, '') if no range found.
    """
    yrs = [int(y) for y in re.findall(r"(?:19|20)\d{2}", title_line)]
    has_present = bool(re.search(r"present|current|now", title_line, re.I))
    if has_present and yrs:
        start = min(yrs)
        end = datetime.now().year
        return float(max(0, end - start)), f"{start}–Present"
    if len(yrs) >= 2:
        start, end = min(yrs), max(yrs)
        return float(max(0, end - start)), f"{start}–{end}"
    if len(yrs) == 1 and has_present:
        end = datetime.now().year
        return float(max(0, end - yrs[0])), f"{yrs[0]}–Present"
    return 0.0, ""


def _extract_experience_items(text: str) -> list[dict]:
    items, current = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        # A title line typically has a year or " at " / " - "; bullets start with • -
        if re.search(r"(19|20)\d{2}", s) or " at " in s.lower():
            if current:
                items.append(current)
            years, span = _role_years(s)
            current = {"title": s, "details": [], "years": years, "span": span}
        elif current and (s.startswith(("•", "-", "*")) or len(s) > 0):
            current["details"].append(s.lstrip("•-* "))
    if current:
        items.append(current)
    return items[:12]


def _extract_bullets(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        s = line.strip().lstrip("•-* ")
        if s:
            out.append(s)
    return out[:20]


# --- Job description structuring -------------------------------------------
def parse_job_description(text: str) -> dict:
    """Extract structured requirements from a job description."""
    low = text.lower()
    required, preferred = _split_required_preferred(text)

    req_skills = normalize_skill_list(_find_terms(required or text, KNOWN_SKILLS))
    pref_skills = normalize_skill_list(_find_terms(preferred, KNOWN_SKILLS)) if preferred else []
    # Anything in preferred that's also required: keep it only in required.
    pref_skills = [s for s in pref_skills if s not in req_skills]

    certifications = normalize_skill_list(_find_terms(text, KNOWN_CERTS))
    soft = normalize_skill_list(_find_terms(text, KNOWN_SOFT_SKILLS))
    education = list(dict.fromkeys(
        t for t in DEGREE_TERMS if re.search(r"(?<![a-z])" + re.escape(t), low)
    ))
    keywords = _top_keywords(text)
    years = estimate_years_experience(text)

    return {
        "required_skills": req_skills,
        "preferred_skills": pref_skills,
        "certifications": certifications,
        "soft_skills": soft,
        "education": education,
        "keywords": keywords,
        "industry_terms": [k for k in keywords if k not in req_skills][:15],
        "min_years_experience": years,
    }


def _split_required_preferred(text: str) -> tuple[str, str]:
    """Roughly separate 'required'/'must have' vs 'preferred'/'nice to have'."""
    lines = text.splitlines()
    required, preferred, bucket = [], [], "required"
    for line in lines:
        low = line.lower()
        if any(k in low for k in ["preferred", "nice to have", "bonus", "plus:"]):
            bucket = "preferred"
        elif any(k in low for k in ["required", "must have", "qualifications", "requirements"]):
            bucket = "required"
        (required if bucket == "required" else preferred).append(line)
    return "\n".join(required), "\n".join(preferred)


_STOPWORDS = set("""a an the and or for to of in on with as is are be will you we our your they this
that at from by have has had not but if then than into over under across per etc role team work
experience years ability strong excellent good knowledge using use used skills skill required must
job description company candidate candidates responsibilities responsibility plus help include including""".split())


def _top_keywords(text: str, limit: int = 25) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{2,}", text.lower())
    freq: dict[str, int] = {}
    for t in tokens:
        t = t.strip(".-")
        if t in _STOPWORDS or len(t) < 3:
            continue
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [w for w, _ in ranked[:limit]]
