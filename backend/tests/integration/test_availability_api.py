from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.main import app
from app.services.availability_service import record_check

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)


@pytest.fixture
def client():
    Base.metadata.create_all(engine)
    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)
    Base.metadata.drop_all(engine)


def test_health_success(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "application": "up", "database": "up"}


def test_health_database_failure(client):
    class BrokenSession:
        def execute(self, statement):
            from sqlalchemy.exc import OperationalError
            raise OperationalError("SELECT 1", {}, RuntimeError("database offline"))
        def rollback(self):
            pass
    def override_db():
        yield BrokenSession()
    app.dependency_overrides[get_db] = override_db
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["database"] == "down"


def test_report_between_health_transitions_and_overlapping_maintenance(client):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db = TestingSession()
    record_check(db, "up", start)
    record_check(db, "down", start.replace(hour=1))
    record_check(db, "up", start.replace(hour=2))
    db.close()
    query = {
        "start": start.isoformat(), "end": start.replace(hour=3).isoformat(),
        "maintenance": [
            f"{start.replace(hour=1).isoformat()}/{start.replace(hour=1, minute=45).isoformat()}",
            f"{start.replace(hour=1, minute=30).isoformat()}/{start.replace(hour=2).isoformat()}",
        ],
    }
    response = client.get("/availability", params=query)
    assert response.status_code == 200
    data = response.json()
    assert data["uptime_seconds"] == 7200
    assert data["downtime_seconds"] == 0
    assert data["maintenance_excluded_seconds"] == 3600
    assert data["availability_percent"] == 100
    assert data["target_achieved"] is True


def test_report_without_previous_checks_is_insufficient(client):
    response = client.get("/availability", params={
        "start": "2026-01-01T00:00:00+00:00", "end": "2026-01-01T01:00:00+00:00",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_data"
    assert response.json()["target_achieved"] is False


@pytest.mark.parametrize("start,end", [
    ("2026-01-01T00:00:00", "2026-01-01T01:00:00"),
    ("2026-01-01T01:00:00+00:00", "2026-01-01T00:00:00+00:00"),
    ("2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
])
def test_invalid_report_ranges(client, start, end):
    response = client.get("/availability", params={"start": start, "end": end})
    assert response.status_code == 422


def test_zero_operating_time_is_not_reported_as_100_percent(client):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db = TestingSession()
    record_check(db, "up", start)
    db.close()
    response = client.get("/availability", params={
        "start": start.isoformat(), "end": start.replace(hour=1).isoformat(),
        "maintenance": [f"{start.isoformat()}/{start.replace(hour=1).isoformat()}"],
    })
    data = response.json()
    assert data["status"] == "no_operating_time"
    assert data["availability_percent"] is None
    assert data["target_achieved"] is False
