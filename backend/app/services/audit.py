"""Audit logging helper — records user actions for compliance."""
from sqlalchemy.orm import Session

from ..models import AuditLog


def log(db: Session, user_id: int | None, action: str, detail: str = "") -> None:
    db.add(AuditLog(user_id=user_id, action=action, detail=detail[:2000]))
    db.commit()
