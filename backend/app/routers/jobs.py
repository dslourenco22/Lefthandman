"""Job-description endpoints: create from text or file, list, update weights."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..database import get_db
from ..models import Candidate, JobDescription
from ..schemas import DEFAULT_WEIGHTS, JobCreate, JobOut, SkillsUpdate, WeightsUpdate
from ..services import audit, parsing
from ..services.nlp import normalize_skill_list, parse_job_description

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _build_job(title: str, text: str, weights: dict | None, user_id: int) -> JobDescription:
    structured = parse_job_description(text)
    return JobDescription(
        title=title or "Untitled role",
        raw_text=text,
        weights=weights or dict(DEFAULT_WEIGHTS),
        created_by=user_id,
        **structured,
    )


@router.post("", response_model=JobOut)
def create_job(payload: JobCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is empty")
    job = _build_job(payload.title, payload.raw_text, payload.weights, user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    audit.log(db, user.id, "create_job", f"job={job.id} title={job.title}")
    return job


@router.post("/upload", response_model=JobOut)
async def upload_job(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    title: Annotated[str, Form()] = "",
    file: UploadFile = File(...),
):
    content = await file.read()
    try:
        parsing.validate_file(file.filename, content)
        parsing.scan_for_malware(content)
    except parsing.FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    text = parsing.extract_text(file.filename, content)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")
    job = _build_job(title or file.filename, text, None, user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    audit.log(db, user.id, "upload_job", f"job={job.id}")
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/{job_id}/skills", response_model=JobOut)
def update_skills(
    job_id: int, payload: SkillsUpdate, user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Manually override a job's required/preferred skills, then re-score every
    candidate already uploaded against the updated criteria."""
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Normalize and de-duplicate; keep required out of preferred.
    req = normalize_skill_list([s.strip() for s in payload.required_skills if s.strip()])
    pref = normalize_skill_list([s.strip() for s in payload.preferred_skills if s.strip()])
    pref = [s for s in pref if s not in req]
    job.required_skills = req
    job.preferred_skills = pref
    db.commit()

    # Re-score existing candidates (keeps uploaded resumes).
    rows = db.query(Candidate.id).filter(Candidate.job_id == job_id).all()
    candidate_ids = [r[0] for r in rows]
    db.refresh(job)
    audit.log(db, user.id, "update_skills",
              f"job={job_id} required={len(req)} preferred={len(pref)}")

    if candidate_ids:
        from ..services.pipeline import rescore_batch
        rescore_batch(candidate_ids)
    return job
def update_weights(
    job_id: int, payload: WeightsUpdate, user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.weights = payload.weights
    db.commit()
    db.refresh(job)
    audit.log(db, user.id, "update_weights", f"job={job_id}")
    return job
