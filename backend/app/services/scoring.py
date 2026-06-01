"""The candidate matching engine.

Computes a configurable weighted score across eight dimensions, combining
exact and semantic skill matching, experience fit, education, certifications,
project/role relevance (embedding similarity), soft skills, and keyword
density. Produces strengths, weaknesses, a recommendation band, and a summary.
"""
from __future__ import annotations

from . import embeddings
from .nlp import normalize_skill_list

DIMENSIONS = [
    "skills", "experience", "education", "certifications",
    "projects", "soft_skills", "keywords",
]

# Recommendation bands keyed by lower bound (inclusive).
BANDS = [
    (90, "Highly Recommended"),
    (80, "Recommended"),
    (70, "Potential Candidate"),
    (0, "Low Match"),
]

EDU_RANK = {
    "high school": 1, "diploma": 1, "associate": 2,
    "bachelor": 3, "b.s": 3, "bsc": 3, "b.a": 3,
    "master": 4, "m.s": 4, "msc": 4, "mba": 4,
    "doctorate": 5, "phd": 5, "ph.d": 5,
}


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    w = {d: float(weights.get(d, 0.0)) for d in DIMENSIONS}
    total = sum(w.values())
    if total <= 0:
        # Fall back to the spec's default distribution.
        return {
            "skills": 0.40, "experience": 0.20, "education": 0.10,
            "certifications": 0.10, "projects": 0.10, "soft_skills": 0.05,
            "keywords": 0.05,
        }
    return {d: v / total for d, v in w.items()}


def _skills_score(job, candidate_skills: list[str]):
    required = job.required_skills or []
    preferred = job.preferred_skills or []
    matched, missing = embeddings.skill_set_coverage(required, candidate_skills)
    req_score = len(matched) / len(required) if required else 1.0
    # Preferred skills give a bonus but never penalize.
    pref_matched, _ = embeddings.skill_set_coverage(preferred, candidate_skills)
    pref_score = len(pref_matched) / len(preferred) if preferred else 0.0
    score = min(1.0, 0.85 * req_score + 0.15 * pref_score)
    return score, matched, missing, pref_matched


def _experience_score(job, years: float) -> float:
    required = job.min_years_experience or 0.0
    if required <= 0:
        return 1.0 if years > 0 else 0.6
    ratio = years / required
    # Full credit at/above requirement; partial credit below; small over-bonus.
    if ratio >= 1:
        return min(1.0, 0.9 + 0.1 * min(ratio - 1, 1))
    return max(0.0, ratio * 0.9)


def _education_score(job, candidate_education: list[dict]) -> float:
    req_levels = [EDU_RANK.get(e, 0) for e in (job.education or [])]
    required = max(req_levels) if req_levels else 0
    cand_levels = [EDU_RANK.get((e.get("level") or "").lower(), 0) for e in candidate_education]
    have = max(cand_levels) if cand_levels else 0
    if required == 0:
        return 1.0 if have > 0 else 0.7
    if have == 0:
        return 0.3
    return min(1.0, have / required)


def _cert_score(job, candidate_certs: list[str]) -> tuple[float, list[str]]:
    required = job.certifications or []
    if not required:
        return (1.0 if candidate_certs else 0.7), []
    matched, missing = embeddings.skill_set_coverage(required, candidate_certs, threshold=0.7)
    return (len(matched) / len(required)), missing


def _projects_score(job, candidate) -> float:
    """Semantic relevance of the candidate's experience+projects to the JD."""
    cand_text = " ".join(
        [candidate.summary or ""]
        + [w.get("title", "") + " " + " ".join(w.get("details", []))
           for w in (candidate.work_experience or [])]
        + [str(p) for p in (candidate.projects or [])]
    ).strip()
    if not cand_text:
        return 0.4
    return embeddings.similarity(job.raw_text[:2000], cand_text[:2000])


def _soft_skills_score(job, candidate) -> float:
    required = job.soft_skills or []
    if not required:
        return 0.7
    text = (candidate.summary or "") + " " + " ".join(
        w.get("title", "") + " " + " ".join(w.get("details", []))
        for w in (candidate.work_experience or [])
    )
    matched, _ = embeddings.skill_set_coverage(required, [text.lower()], threshold=0.55)
    # The above is coarse; count direct mentions too.
    hits = sum(1 for s in required if s.lower() in text.lower())
    return min(1.0, max(len(matched), hits) / len(required))


def _keyword_score(job, candidate) -> float:
    keywords = job.keywords or []
    if not keywords:
        return 0.7
    blob = " ".join(filter(None, [
        candidate.summary or "",
        " ".join(candidate.skills_raw or []),
        " ".join(w.get("title", "") for w in (candidate.work_experience or [])),
    ])).lower()
    hits = sum(1 for k in keywords if k in blob)
    return min(1.0, hits / max(8, len(keywords) * 0.5))


def _most_relevant_experience(job, candidate) -> tuple[float, str]:
    """Pick the work-experience entry most relevant to the job and return
    (its duration in years, a human-readable source string).

    Relevance is the semantic similarity of each role's text to the job text.
    Falls back to the longest role, then to the candidate's total years.
    """
    roles = candidate.work_experience or []
    roles = [r for r in roles if isinstance(r, dict)]
    if not roles:
        return float(candidate.years_experience or 0.0), ""

    job_text = (job.raw_text or "")[:2000]
    best, best_sim = None, -1.0
    for r in roles:
        role_text = (r.get("title", "") + " " + " ".join(r.get("details", []))).strip()
        if not role_text:
            continue
        try:
            sim = embeddings.similarity(job_text, role_text)
        except Exception:
            sim = 0.0
        if sim > best_sim:
            best_sim, best = sim, r

    if best is None or best_sim <= 0:
        best = max(roles, key=lambda r: r.get("years", 0) or 0)

    years = float(best.get("years") or 0.0)
    title = best.get("title", "").strip()
    span = best.get("span", "")
    # Keep the source label concise: title without trailing date noise + span.
    label = title
    if span and span not in title:
        label = f"{title} ({span})"
    if years <= 0:  # no parseable span on the chosen role; show total instead
        return float(candidate.years_experience or 0.0), label
    return years, label


def score_candidate(job, candidate) -> dict:
    """Compute the full score breakdown for one candidate against one job."""
    weights = _normalize_weights(job.weights or {})
    cand_skills = normalize_skill_list(candidate.skills_raw or [])

    skills, matched, missing, pref_matched = _skills_score(job, cand_skills)
    experience = _experience_score(job, candidate.years_experience or 0.0)
    education = _education_score(job, candidate.education or [])
    certifications, missing_certs = _cert_score(job, candidate.certifications or [])
    projects = _projects_score(job, candidate)
    soft = _soft_skills_score(job, candidate)
    keywords = _keyword_score(job, candidate)

    per_dim = {
        "skills": skills, "experience": experience, "education": education,
        "certifications": certifications, "projects": projects,
        "soft_skills": soft, "keywords": keywords,
    }
    overall = sum(per_dim[d] * weights[d] for d in DIMENSIONS) * 100
    overall = round(overall, 1)

    strengths, weaknesses = _strengths_weaknesses(
        per_dim, matched, missing, missing_certs, candidate, job
    )
    recommendation, reason = _recommend(overall, missing, candidate, job)
    summary = _summarize(candidate, overall, matched, missing, recommendation)

    rel_years, rel_source = _most_relevant_experience(job, candidate)

    return {
        "overall": overall,
        "breakdown": {
            **{d: round(per_dim[d] * 100, 1) for d in DIMENSIONS},
            "_relevant_years": round(rel_years, 1),
            "_relevant_source": rel_source,
        },
        "matched_skills": matched,
        "missing_skills": missing,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "recommendation_reason": reason,
        "summary": summary,
    }


def _strengths_weaknesses(per_dim, matched, missing, missing_certs, candidate, job):
    strengths, weaknesses = [], []
    if candidate.years_experience and job.min_years_experience and \
            candidate.years_experience >= job.min_years_experience:
        strengths.append(
            f"{candidate.years_experience:.0f} years of experience "
            f"(meets the {job.min_years_experience:.0f}+ year requirement)"
        )
    if matched:
        top = ", ".join(matched[:5])
        strengths.append(f"Matches key skills: {top}")
    if candidate.certifications:
        strengths.append("Relevant certifications: " + ", ".join(candidate.certifications[:3]))
    if per_dim["projects"] >= 0.6:
        strengths.append("Project/role history is closely aligned with the job")

    if missing:
        weaknesses.append("Missing required skills: " + ", ".join(missing[:5]))
    if missing_certs:
        weaknesses.append("Missing certifications: " + ", ".join(missing_certs[:3]))
    if job.min_years_experience and (candidate.years_experience or 0) < job.min_years_experience:
        weaknesses.append(
            f"Below the {job.min_years_experience:.0f}-year experience requirement "
            f"({candidate.years_experience:.0f} found)"
        )
    if per_dim["education"] < 0.5:
        weaknesses.append("Education may not meet the stated requirement")
    return strengths[:6], weaknesses[:6]


def _recommend(overall, missing, candidate, job):
    band = next(name for low, name in BANDS if overall >= low)
    bits = [f"Overall match {overall:.0f}%."]
    if not missing:
        bits.append("All required skills are present.")
    else:
        bits.append(f"{len(missing)} required skill(s) not found.")
    if band in ("Highly Recommended", "Recommended"):
        bits.append("Recommend advancing to interview.")
    elif band == "Potential Candidate":
        bits.append("Consider for interview if the pipeline is thin.")
    else:
        bits.append("Likely below the bar for this role.")
    return band, " ".join(bits)


def _summarize(candidate, overall, matched, missing, recommendation):
    name = candidate.name or "This candidate"
    parts = [f"{name} scores {overall:.0f}% against the role ({recommendation})."]
    if matched:
        parts.append(f"Strong on {', '.join(matched[:3])}.")
    if missing:
        parts.append(f"Gaps in {', '.join(missing[:3])}.")
    return " ".join(parts)
