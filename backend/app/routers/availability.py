from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from app.database.database import SessionLocal, get_db
from app.models.availability import AvailabilityEvent
from app.services.availability_service import availability_report, record_check

router = APIRouter(tags=["availability"])
_database_outage_started: datetime | None = None


def monitor_once():
    """Sample the running service and database; buffer a DB outage until storage returns."""
    global _database_outage_started
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        previous = db.query(AvailabilityEvent).order_by(AvailabilityEvent.checked_at.desc()).first()
        if previous is not None:
            previous_time = previous.checked_at
            if previous_time.tzinfo is None:
                previous_time = previous_time.replace(tzinfo=timezone.utc)
            # If this process was stopped, represent the missed-monitor interval as downtime.
            if previous.status == "up" and (now - previous_time).total_seconds() > 60:
                record_check(db, "down", previous_time + timedelta(seconds=60))
        mark_database_up(db, now)
    except SQLAlchemyError:
        db.rollback()
        if _database_outage_started is None:
            _database_outage_started = now
    finally:
        db.close()


def mark_database_up(db: Session, now: datetime | None = None):
    global _database_outage_started
    now = now or datetime.now(timezone.utc)
    if _database_outage_started is not None:
        record_check(db, "down", _database_outage_started)
        _database_outage_started = None
    record_check(db, "up", now)


@router.get("/availability")
def get_availability(
    start: datetime = Query(...), end: datetime = Query(...),
    maintenance: list[str] = Query(default=[]), db: Session = Depends(get_db),
):
    windows = []
    for item in maintenance:
        try:
            left, right = item.split("/", 1)
            windows.append((datetime.fromisoformat(left), datetime.fromisoformat(right)))
        except ValueError as exc:
            return JSONResponse(status_code=422, content={"detail": "maintenance must use start/end ISO datetime pairs"})
    try:
        report = availability_report(db, start, end, windows)
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    return report
