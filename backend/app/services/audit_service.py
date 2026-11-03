from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.models.audit_log import AuditLog


def log_audit(
    db: Session,
    user_id: int,
    action: str,
    entity: str,
    entity_id: int,
) -> AuditLog:
    if not user_id or user_id <= 0:
        raise BadRequestError("Invalid user id")
    if not action or not action.strip():
        raise BadRequestError("Invalid action")
    if not entity or not entity.strip():
        raise BadRequestError("Invalid entity")
    if not entity_id or entity_id <= 0:
        raise BadRequestError("Invalid entity id")

    audit_log = AuditLog(
        user_id=user_id,
        action=action.strip(),
        entity=entity.strip(),
        entity_id=entity_id,
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def get_audit_logs(
    db: Session,
    user_id: int | None = None,
    entity: str | None = None,
    action: str | None = None,
) -> list[AuditLog]:
    query = db.query(AuditLog)

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    if entity:
        query = query.filter(AuditLog.entity == entity)

    if action:
        query = query.filter(AuditLog.action == action)

    return query.order_by(AuditLog.timestamp.desc()).all()
