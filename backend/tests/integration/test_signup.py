import asyncio
from datetime import datetime, timedelta, timezone
from ipaddress import ip_network

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import State

from app.core.auth_limits import AuthBodyLimit, AuthRateLimiter
from app.core.password_security import verify_password
from app.database.database import Base, get_db, settings
from app.main import app
from app.models.audit_log import AuditLog
from app.models.product import Product
from app.models.user import User
from app.routers import product, reports, transactions
from app.services import product_service


@pytest.fixture
def signup_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def db():
        with sessions() as session:
            yield session

    for dependency in (get_db, product.get_db, reports.get_db, transactions.get_db):
        monkeypatch.setitem(app.dependency_overrides, dependency, db)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-only-signing-key-with-32-plus-characters")
    monkeypatch.setattr(settings, "REGISTRATION_ENABLED", True)
    monkeypatch.setattr(app, "state", State({"auth_limiter": AuthRateLimiter()}))
    with TestClient(app) as client:
        yield client, sessions
    engine.dispose()


PASSWORD = "Fixture-only-872!"


def test_signup_login_and_employee_boundary(signup_client):
    client, sessions = signup_client
    details = {"username": "signup_employee", "password": PASSWORD}
    response = client.post("/auth/register", json=details)
    assert response.status_code == 201
    account = response.json()
    assert account == {"id": account["id"], "username": details["username"], "role": "employee"}
    with sessions() as db:
        record = db.get(User, account["id"])
        assert record.hashed_password != PASSWORD
        assert verify_password(PASSWORD, record.hashed_password)
    assert client.post("/auth/register", json=details).status_code == 409

    login = client.post("/auth/login", json=details)
    assert login.status_code == 200
    assert login.headers["cache-control"] == "no-store"
    token = login.json()["access_token"]
    claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    assert set(claims) == {"sub", "iat", "exp"}
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/auth/me", headers=headers)
    assert me.json() == account
    assert me.headers["cache-control"] == "no-store"
    assert client.get("/products/", headers=headers).status_code == 200
    assert client.get("/reports/", headers=headers).status_code == 403
    assert client.post("/products/", headers=headers, json={"name": "No", "category": "Test", "price": 10, "quantity": 1}).status_code == 403
    assert client.put("/products/1", headers=headers, json={"name": "No"}).status_code == 403
    assert client.delete("/products/1", headers=headers).status_code == 403


@pytest.mark.parametrize("details", [
    {},
    {"username": "invalid name", "password": PASSWORD},
    {"username": "weak_password", "password": "Short1!"},
    {"username": "weak_password", "password": "lettersonlypassword"},
    {"username": "admin_attempt", "password": PASSWORD, "role": "admin"},
    {"username": "admin_attempt", "password": PASSWORD, "id": 1},
])
def test_rejects_invalid_registration_without_exposing_input(signup_client, details):
    client, sessions = signup_client
    response = client.post("/auth/register", json=details)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert all("input" not in error for error in response.json()["detail"])
    with sessions() as db:
        assert db.query(User).count() == 0


def test_registration_toggle_and_limits(signup_client, monkeypatch):
    client, _ = signup_client
    first = {"username": "first_signup", "password": PASSWORD}
    second = {"username": "next_signup", "password": PASSWORD}
    monkeypatch.setattr(settings, "REGISTRATION_ENABLED", False)
    assert client.post("/auth/register", json=first).status_code == 403
    monkeypatch.setattr(settings, "REGISTRATION_ENABLED", True)
    monkeypatch.setattr(settings, "REGISTRATION_REQUESTS_PER_MINUTE", 1)
    assert client.post("/auth/register", json=first).status_code == 201
    limited = client.post("/auth/register", json=second)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0

    monkeypatch.setattr(settings, "LOGIN_REQUESTS_PER_MINUTE", 1)
    assert client.post("/auth/login", json=second).status_code == 401
    assert client.post("/auth/login", json=first).status_code == 429


def test_untrusted_socket_cannot_spoof_forwarded_identity(signup_client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_REQUESTS_PER_MINUTE", 1)
    app.state.auth_limiter = AuthRateLimiter(trusted_proxies=(ip_network("10.0.0.0/24"),))
    with TestClient(app, client=("198.51.100.10", 45000)) as client:
        payload = {"username": "missing", "password": PASSWORD}
        assert client.post("/auth/login", json=payload).status_code == 401
        assert client.post("/auth/login", json=payload, headers={
            "X-Forwarded-For": "203.0.113.25", "CF-Connecting-IP": "203.0.113.26",
        }).status_code == 429


def test_trusted_proxy_chain_keeps_separate_client_quotas(signup_client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_REQUESTS_PER_MINUTE", 1)
    app.state.auth_limiter = AuthRateLimiter(trusted_proxies=(ip_network("10.0.0.0/24"),))
    with TestClient(app, client=("10.0.0.1", 45000)) as client:
        payload = {"username": "missing", "password": PASSWORD}
        for forwarded, status in [
            ("198.51.100.10, 10.0.0.2", 401),
            ("203.0.113.25, 198.51.100.10, 10.0.0.2", 429),
            ("198.51.100.11, 10.0.0.2", 401),
            ("198.51.100.12, malformed, 10.0.0.2", 401),
            ("198.51.100.13, malformed, 10.0.0.2", 429),
        ]:
            assert client.post("/auth/login", json=payload, headers={"X-Forwarded-For": forwarded}).status_code == status


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login"])
def test_oversized_auth_requests_are_rejected_before_json_validation(signup_client, path):
    client, sessions = signup_client
    response = client.post(path, content=b"x" * 4097, headers={"Origin": settings.FRONTEND_ORIGIN})
    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == settings.FRONTEND_ORIGIN
    with sessions() as db:
        assert db.query(User).count() == 0


def test_streaming_auth_body_is_capped_without_content_length():
    async def unreachable_app(scope, receive, send):
        pytest.fail("Oversized body reached the app")

    messages = iter([
        {"type": "http.request", "body": b"x" * 4096, "more_body": True},
        {"type": "http.request", "body": b"x", "more_body": True},
    ])
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    asyncio.run(AuthBodyLimit(unreachable_app)(
        {"type": "http", "method": "POST", "path": "/auth/login", "headers": []}, receive, send,
    ))
    assert sent[0]["status"] == 413


def test_me_uses_database_role_and_rejects_expired_or_unsigned_session(signup_client):
    client, sessions = signup_client
    account = client.post("/auth/register", json={"username": "role_test", "password": PASSWORD}).json()
    token = client.post("/auth/login", json={"username": "role_test", "password": PASSWORD}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    with sessions.begin() as db:
        db.get(User, account["id"]).role = "admin"
    assert client.get("/auth/me", headers=headers).json()["role"] == "admin"
    expired = jwt.encode({"sub": str(account["id"]), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, settings.JWT_SECRET_KEY, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_product_admin_actions_are_audited_once(signup_client):
    client, sessions = signup_client
    account = client.post("/auth/register", json={"username": "admin_fixture", "password": PASSWORD}).json()
    with sessions.begin() as db:
        db.get(User, account["id"]).role = "admin"
    token = client.post("/auth/login", json={"username": "admin_fixture", "password": PASSWORD}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/products/", json={"name": "Demo", "category": "Test", "price": 3, "quantity": 2}, headers=headers)
    assert created.status_code == 201
    product_id = created.json()["id"]
    assert client.put(f"/products/{product_id}", json={"name": "Edited"}, headers=headers).status_code == 200
    assert client.delete(f"/products/{product_id}", headers=headers).status_code == 200
    with sessions() as db:
        changes = db.query(AuditLog).order_by(AuditLog.id).all()
        assert [(log.action, log.entity, log.entity_id, log.user_id) for log in changes] == [
            (name, "product", product_id, account["id"]) for name in ("create_product", "update_product", "delete_product")
        ]
        assert all(log.timestamp is not None for log in changes)


@pytest.mark.parametrize("action", ["create", "update", "delete"])
def test_failed_product_audit_rolls_back_api_mutation(signup_client, monkeypatch, action):
    client, sessions = signup_client
    details = {"username": "audit_admin", "password": PASSWORD}
    account = client.post("/auth/register", json=details).json()
    with sessions.begin() as db:
        db.get(User, account["id"]).role = "admin"
    token = client.post("/auth/login", json=details).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    payload = {"name": "Original", "category": "Test", "price": 3, "quantity": 2}
    original = client.post("/products/", json=payload, headers=auth).json()
    log = product_service.log_audit

    def fail_after_audit_flush(*args, **kwargs):
        log(*args, **kwargs)
        raise SQLAlchemyError("simulated audit write failure")

    monkeypatch.setattr(product_service, "log_audit", fail_after_audit_flush)
    path = f"/products/{original['id']}"
    if action == "create":
        response = client.post("/products/", json={**payload, "name": "Second"}, headers=auth)
    elif action == "update":
        response = client.put(path, json={"name": "Edited"}, headers=auth)
    else:
        response = client.delete(path, headers=auth)
    assert response.status_code == 500
    assert "simulated" not in response.text
    with sessions() as db:
        assert [(row.id, row.name, row.quantity) for row in db.query(Product)] == [(original["id"], "Original", 2)]
        assert [row.action for row in db.query(AuditLog)] == ["create_product"]


def test_recent_transactions_respect_limit(signup_client):
    client, sessions = signup_client
    account = client.post("/auth/register", json={"username": "activity_fixture", "password": PASSWORD}).json()
    with sessions.begin() as db:
        db.get(User, account["id"]).role = "admin"
    token = client.post("/auth/login", json={"username": "activity_fixture", "password": PASSWORD}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/products/", json={"name": "Activity", "category": "Test", "price": 1, "quantity": 0}, headers=headers)
    assert created.status_code == 201
    product_id = created.json()["id"]
    for index in range(2):
        movement = client.post("/transactions/", json={
            "product_id": product_id, "transaction_type": "ADD",
            "quantity": 1, "user_id": account["id"], "reference": f"Activity {index}",
        }, headers=headers)
        assert movement.status_code == 201
    recent = client.get("/transactions/?limit=1", headers=headers)
    assert recent.status_code == 200
    assert [row["reference"] for row in recent.json()] == ["Activity 1"]
    assert len(client.get("/transactions/", headers=headers).json()) == 2
    assert client.get("/transactions/?limit=0", headers=headers).status_code == 422
