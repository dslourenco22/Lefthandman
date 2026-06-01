"""Export endpoints (CSV / Excel / PDF) for a job's ranked candidates."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..database import get_db
from ..models import Candidate, JobDescription
from ..services import audit, export

router = APIRouter(prefix="/api/jobs/{job_id}/export", tags=["export"])

MEDIA = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _ranked(db: Session, job_id: int) -> list[Candidate]:
    candidates = (
        db.query(Candidate)
        .filter(Candidate.job_id == job_id, Candidate.status == "scored")
        .all()
    )
    candidates.sort(key=lambda c: c.score.overall if c.score else 0, reverse=True)
    return candidates


@router.get("/{fmt}")
def export_results(
    job_id: int, fmt: str, user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if fmt not in MEDIA:
        raise HTTPException(status_code=400, detail="Format must be csv, xlsx, or pdf")

    ranked = _ranked(db, job_id)
    if fmt == "csv":
        body = export.to_csv(ranked)
    elif fmt == "xlsx":
        body = export.to_excel(ranked, job.title)
    else:
        body = export.to_pdf(ranked, job.title)

    audit.log(db, user.id, "export", f"job={job_id} fmt={fmt}")
    filename = f"ranking_job_{job_id}.{fmt}"
    return Response(
        content=body, media_type=MEDIA[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
