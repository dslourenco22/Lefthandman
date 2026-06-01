"""Resume upload (single + bulk) and processing-status endpoints."""
from typing import Annotated

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile,
)
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..database import get_db
from ..models import Candidate, JobDescription, Resume
from ..schemas import ProcessingStatus
from ..services import audit, parsing
from ..services.pipeline import process_batch

router = APIRouter(prefix="/api/jobs/{job_id}/resumes", tags=["resumes"])


@router.post("", response_model=ProcessingStatus)
async def upload_resumes(
    job_id: int,
    background: BackgroundTasks,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    files: list[UploadFile] = File(...),
):
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    new_ids: list[int] = []
    errors: list[str] = []
    for f in files:
        content = await f.read()
        try:
            parsing.validate_file(f.filename, content)
            parsing.scan_for_malware(content)
            text = parsing.extract_text(f.filename, content)
            if not text.strip():
                raise parsing.FileValidationError("no extractable text")
        except parsing.FileValidationError as e:
            errors.append(f"{f.filename}: {e}")
            continue

        candidate = Candidate(job_id=job_id, status="pending", name=f.filename)
        db.add(candidate)
        db.flush()
        candidate.resume = Resume(
            candidate_id=candidate.id, filename=f.filename,
            content_type=f.content_type or "", raw_text=text, byte_size=len(content),
        )
        db.commit()
        new_ids.append(candidate.id)

    if new_ids:
        # Background processing keeps the request fast for large batches.
        # For 500+ resumes in production, swap this for a Celery/RQ worker
        # (process_batch is already worker-friendly).
        background.add_task(process_batch, new_ids)
    audit.log(db, user.id, "upload_resumes",
              f"job={job_id} accepted={len(new_ids)} rejected={len(errors)}")
    return _status(db, job_id)


@router.get("/status", response_model=ProcessingStatus)
def processing_status(job_id: int, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    if not db.get(JobDescription, job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return _status(db, job_id)


def _status(db: Session, job_id: int) -> ProcessingStatus:
    rows = db.query(Candidate.status).filter(Candidate.job_id == job_id).all()
    counts = {"pending": 0, "processing": 0, "scored": 0, "error": 0}
    for (s,) in rows:
        counts[s] = counts.get(s, 0) + 1
    total = len(rows)
    return ProcessingStatus(
        job_id=job_id, total=total, scored=counts["scored"],
        processing=counts["processing"], pending=counts["pending"],
        errored=counts["error"],
        done=total > 0 and counts["pending"] == 0 and counts["processing"] == 0,
    )
