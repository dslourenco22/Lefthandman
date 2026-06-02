"""Ranking, candidate detail, and comparison endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..database import get_db
from ..models import Candidate, CandidateComparison, JobDescription
from ..schemas import CandidateOut, RankedCandidate
from ..services import audit

router = APIRouter(prefix="/api/jobs/{job_id}", tags=["ranking"])

SORT_FIELDS = {"match", "experience", "education", "certifications", "name"}


@router.get("/ranking", response_model=list[RankedCandidate])
def ranking(
    job_id: int,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    sort_by: str = Query("match"),
    search: str = Query(""),
    min_score: float = Query(0.0),
    recommendation: str = Query(""),
):
    if not db.get(JobDescription, job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    candidates = (
        db.query(Candidate)
        .filter(Candidate.job_id == job_id, Candidate.status == "scored")
        .all()
    )

    if search:
        q = search.lower()
        candidates = [
            c for c in candidates
            if q in (c.name or "").lower() or q in (c.email or "").lower()
            or any(q in s.lower() for s in (c.skills_raw or []))
        ]
    if recommendation:
        candidates = [c for c in candidates if c.score and c.score.recommendation == recommendation]
    candidates = [c for c in candidates if c.score and c.score.overall >= min_score]

    def key(c: Candidate):
        s = c.score
        return {
            "match": s.overall if s else 0,
            "experience": c.years_experience,
            "education": len(c.education or []),
            "certifications": len(c.certifications or []),
            "name": c.name.lower(),
        }.get(sort_by if sort_by in SORT_FIELDS else "match", s.overall if s else 0)

    reverse = sort_by != "name"
    candidates.sort(key=key, reverse=reverse)
    return [RankedCandidate(rank=i, candidate=c) for i, c in enumerate(candidates, start=1)]


@router.get("/candidates/{candidate_id}", response_model=CandidateOut)
def candidate_detail(
    job_id: int, candidate_id: int, user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    c = db.get(Candidate, candidate_id)
    if not c or c.job_id != job_id:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c


@router.get("/candidates/{candidate_id}/resume")
def candidate_resume(
    job_id: int, candidate_id: int, user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Return the stored (extracted) text of a candidate's resume so it can be
    viewed in-app without opening the original file."""
    c = db.get(Candidate, candidate_id)
    if not c or c.job_id != job_id:
        raise HTTPException(status_code=404, detail="Candidate not found")
    resume = c.resume
    if not resume:
        raise HTTPException(status_code=404, detail="No resume on file")
    return {
        "filename": resume.filename,
        "content_type": resume.content_type,
        "text": resume.raw_text or "",
    }


@router.get("/compare", response_model=list[CandidateOut])
def compare(
    job_id: int,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    ids: Annotated[list[int], Query()] = [],
):
    if not ids:
        raise HTTPException(status_code=400, detail="Provide candidate ids to compare")
    rows = (
        db.query(Candidate)
        .filter(Candidate.job_id == job_id, Candidate.id.in_(ids))
        .all()
    )
    db.add(CandidateComparison(job_id=job_id, candidate_ids=ids, created_by=user.id))
    db.commit()
    return rows
