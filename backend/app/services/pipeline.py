"""Orchestrates resume processing: parse -> persist candidate -> score.

Designed to run inside a background task. Each candidate is committed
independently so a single bad file never fails the whole batch, and the
job's progress can be polled while processing continues.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Candidate, CandidateScore, JobDescription, Skill
from .nlp import parse_resume
from .scoring import score_candidate


def _upsert_skills(db: Session, names: list[str]) -> list[Skill]:
    out = []
    for name in names:
        skill = db.query(Skill).filter(Skill.canonical == name).first()
        if not skill:
            skill = Skill(canonical=name)
            db.add(skill)
            db.flush()
        out.append(skill)
    return out


def process_candidate(candidate_id: int) -> None:
    """Parse the candidate's resume text and compute its score."""
    db = SessionLocal()
    try:
        candidate = db.get(Candidate, candidate_id)
        if not candidate:
            return
        candidate.status = "processing"
        db.commit()

        parsed = parse_resume(candidate.resume.raw_text)
        for field in (
            "name", "email", "phone", "linkedin", "github", "location",
            "summary", "skills_raw", "certifications", "education",
            "work_experience", "projects", "languages", "years_experience",
        ):
            setattr(candidate, field, parsed.get(field) or getattr(candidate, field))

        candidate.skills = _upsert_skills(db, candidate.skills_raw or [])

        job = db.get(JobDescription, candidate.job_id)
        result = score_candidate(job, candidate)

        score = candidate.score or CandidateScore(candidate_id=candidate.id)
        for k, v in result.items():
            setattr(score, k, v)
        if not candidate.score:
            db.add(score)
        candidate.status = "scored"
        db.commit()
    except Exception as exc:  # noqa: BLE001 - record and move on
        db.rollback()
        c = db.get(Candidate, candidate_id)
        if c:
            c.status = "error"
            c.summary = f"Processing error: {exc}"[:1000]
            db.commit()
    finally:
        db.close()


def process_batch(candidate_ids: list[int]) -> None:
    for cid in candidate_ids:
        process_candidate(cid)


def rescore_candidate(candidate_id: int) -> None:
    """Re-run only the scoring step for a candidate against its (now updated)
    job, reusing the already-parsed resume data. Used when job skills change."""
    db = SessionLocal()
    try:
        candidate = db.get(Candidate, candidate_id)
        if not candidate:
            return
        job = db.get(JobDescription, candidate.job_id)
        if not job:
            return
        result = score_candidate(job, candidate)
        score = candidate.score or CandidateScore(candidate_id=candidate.id)
        for k, v in result.items():
            setattr(score, k, v)
        if not candidate.score:
            db.add(score)
        candidate.status = "scored"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        c = db.get(Candidate, candidate_id)
        if c:
            c.status = "error"
            c.summary = f"Re-scoring error: {exc}"[:1000]
            db.commit()
    finally:
        db.close()


def rescore_batch(candidate_ids: list[int]) -> None:
    for cid in candidate_ids:
        rescore_candidate(cid)
