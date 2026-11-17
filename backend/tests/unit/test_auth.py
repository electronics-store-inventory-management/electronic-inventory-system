from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core import auth_limits
from app.core.auth import ALGORITHM, get_current_user, require_admin
from app.database.database import settings
from app.models.user import User


@pytest.fixture
def auth_db(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "fixture-signing-key-for-unit-tests-only")
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    with Session(engine) as db:
        db.add(User(id=1, username="unit_admin", hashed_password="unused", role="admin"))
        db.commit()
        yield db
    engine.dispose()


def bearer_token(user_id=1, expires_in=60):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    token = jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return f"Bearer {token}"


@pytest.mark.parametrize("authorization", [None, "Basic unused", "Bearer "])
def test_requests_without_bearer_credentials_are_denied(auth_db, authorization):
    with pytest.raises(HTTPException) as error:
        get_current_user(authorization, auth_db)
    assert error.value.status_code == 401


def test_expired_session_is_denied(auth_db):
    with pytest.raises(HTTPException) as error:
        get_current_user(bearer_token(expires_in=-60), auth_db)
    assert error.value.status_code == 401


def test_deleted_account_loses_access_with_an_unexpired_session(auth_db):
    session = bearer_token()
    auth_db.delete(auth_db.get(User, 1))
    auth_db.commit()
    with pytest.raises(HTTPException) as error:
        get_current_user(session, auth_db)
    assert error.value.status_code == 401


def test_role_change_takes_effect_for_an_existing_session(auth_db):
    session = bearer_token()
    assert require_admin(get_current_user(session, auth_db))["role"] == "admin"
    auth_db.get(User, 1).role = "employee"
    auth_db.commit()
    employee = get_current_user(session, auth_db)
    assert employee["role"] == "employee"
    with pytest.raises(HTTPException) as error:
        require_admin(employee)
    assert error.value.status_code == 403


def test_authentication_rate_limit_expires_and_keeps_actions_separate(monkeypatch):
    now = 100.0
    monkeypatch.setattr(auth_limits, "monotonic", lambda: now)
    limiter = auth_limits.AuthRateLimiter(window_seconds=10)
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 3000)})

    limiter.check(request, "login", 1)
    now = 103.0
    with pytest.raises(HTTPException) as error:
        limiter.check(request, "login", 1)
    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "7"}
    limiter.check(request, "register", 1)

    now = 110.0
    limiter.check(request, "login", 1)
