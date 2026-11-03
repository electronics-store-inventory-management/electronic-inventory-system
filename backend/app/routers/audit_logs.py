from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.database.database import SessionLocal
from app.schemas.audit_log import AuditLogResponse
from app.services.audit_service import get_audit_logs

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get(
    "/",
    response_model=list[AuditLogResponse],
)
def list_audit_logs(
    user_id: int | None = Query(default=None, gt=0),
    entity: str | None = Query(default=None),
    action: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    return get_audit_logs(db, user_id=user_id, entity=entity, action=action)
