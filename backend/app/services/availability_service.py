from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.availability import AvailabilityEvent

TARGET_PERCENT = 99.0


def record_check(db: Session, status: str, checked_at: datetime | None = None):
    checked_at = checked_at or datetime.now(timezone.utc)
    # Keep each periodic sample so a later process restart can reveal an unobserved gap.
    db.add(AvailabilityEvent(checked_at=checked_at, status=status))
    db.commit()


def availability_report(db: Session, start: datetime, end: datetime, maintenance=()):
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("start and end must be timezone-aware, with end after start")
    events = db.scalars(
        select(AvailabilityEvent)
        .where(AvailabilityEvent.checked_at <= end)
        .order_by(AvailabilityEvent.checked_at)
    ).all()
    # SQLite drops timezone metadata for DateTime columns; persisted values are UTC.
    for event in events:
        if event.checked_at.tzinfo is None:
            event.checked_at = event.checked_at.replace(tzinfo=timezone.utc)
    normalized_windows = []
    for left, right in maintenance:
        if left.tzinfo is None or right.tzinfo is None or right <= left:
            raise ValueError("maintenance windows must be timezone-aware, with end after start")
        left, right = max(left, start), min(right, end)
        if right > left:
            normalized_windows.append((left, right))
    normalized_windows.sort()
    merged_windows = []
    for left, right in normalized_windows:
        if merged_windows and left <= merged_windows[-1][1]:
            merged_windows[-1] = (merged_windows[-1][0], max(right, merged_windows[-1][1]))
        else:
            merged_windows.append((left, right))

    status = "unknown"
    cursor = start
    # Carry forward the state at the start of the report window.
    for event in events:
        if event.checked_at <= start:
            status = event.status
        else:
            break
    changes = [e for e in events if start < e.checked_at < end]
    changes.append(AvailabilityEvent(checked_at=end, status=status))
    total = up = excluded = 0.0
    for event in changes:
        boundary = min(max(event.checked_at, cursor), end)
        duration = max(0.0, (boundary - cursor).total_seconds())
        excluded_duration = 0.0
        for maintenance_start, maintenance_end in merged_windows:
            left, right = max(cursor, maintenance_start), min(boundary, maintenance_end)
            if right > left:
                excluded_duration += (right - left).total_seconds()
        counted = max(0.0, duration - excluded_duration)
        total += counted
        excluded += excluded_duration
        if status == "up":
            up += counted
        cursor = boundary
        status = event.status
    percent = (up / total * 100) if total else None
    has_baseline = any(event.checked_at <= start for event in events)
    return {
        "start": start.isoformat(), "end": end.isoformat(),
        "uptime_seconds": round(up, 3), "downtime_seconds": round(total - up, 3),
        "maintenance_excluded_seconds": round(excluded, 3),
        "availability_percent": round(percent, 4) if percent is not None else None,
        "target_percent": TARGET_PERCENT,
        "target_achieved": percent >= TARGET_PERCENT if percent is not None and has_baseline else False,
        "status": "no_operating_time" if total == 0 else "insufficient_data" if not has_baseline else "reported",
    }
