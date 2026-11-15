from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.database.database import Base
from app.services.availability_service import availability_report, record_check


def test_tracks_downtime_and_maintenance_exclusion():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record_check(session, "up", start)
    record_check(session, "down", start.replace(hour=1))
    record_check(session, "up", start.replace(hour=2))

    report = availability_report(session, start, start.replace(hour=3))
    assert report["uptime_seconds"] == 7200
    assert report["downtime_seconds"] == 3600
    assert report["target_achieved"] is False

    report = availability_report(
        session, start, start.replace(hour=3),
        [(start.replace(hour=1), start.replace(hour=2))],
    )
    assert report["maintenance_excluded_seconds"] == 3600
    assert report["availability_percent"] == 100
    assert report["target_achieved"] is True
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_repeated_health_state_does_not_create_duplicate_transitions():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record_check(session, "up", timestamp)
    record_check(session, "up", timestamp.replace(minute=1))
    report = availability_report(session, timestamp, timestamp.replace(hour=1))
    assert report["availability_percent"] == 100
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_exactly_99_percent_meets_availability_target():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record_check(session, "up", start)
    record_check(session, "down", start + timedelta(seconds=99))
    record_check(session, "up", start + timedelta(seconds=100))
    report = availability_report(session, start, start + timedelta(seconds=100))
    assert report["availability_percent"] == 99
    assert report["target_achieved"] is True
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_monitor_detects_process_gap_after_restart(monkeypatch):
    from app.models.availability import AvailabilityEvent
    from app.routers import availability

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    previous = datetime.now(timezone.utc) - timedelta(minutes=3)
    session = factory()
    record_check(session, "up", previous)
    session.close()
    monkeypatch.setattr(availability, "SessionLocal", factory)
    monkeypatch.setattr(availability, "_database_outage_started", None)

    availability.monitor_once()

    session = factory()
    events = session.scalars(select(AvailabilityEvent).order_by(AvailabilityEvent.checked_at)).all()
    assert [event.status for event in events] == ["up", "down", "up"]
    assert events[1].checked_at.replace(tzinfo=timezone.utc) == previous + timedelta(seconds=60)
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()
