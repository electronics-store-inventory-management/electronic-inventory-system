"""Integration checks for an explicitly provisioned, disposable local PostgreSQL database."""
from concurrent.futures import ThreadPoolExecutor
from os import environ
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import State

from app import cli
from app.core.auth_limits import AuthRateLimiter
from app.core.password_security import verify_password
from app.database.database import Settings, get_db, settings
from app.main import app
from app.models.audit_log import AuditLog
from app.models.product import Product
from app.models.transaction import InventoryTransaction
from app.models.user import User
from app.routers import auth
from test_migrations import upgrade_database


@pytest.fixture
def test_database_url():
    value = environ.get("ELECTROSTOCK_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("Set ELECTROSTOCK_TEST_POSTGRES_URL to a disposable local test database.")
    url = make_url(value)
    if (
        url.drivername not in {"postgresql", "postgresql+psycopg2"} or url.host not in {"localhost", "127.0.0.1"}
        or not url.port or not (url.database or "").startswith("electrostock_test_") or url.query
    ):
        pytest.fail("The test DSN must target an explicitly ported local electrostock_test_ database without query options.")
    return url.set(drivername="postgresql+psycopg2")


@pytest.fixture
def postgres(test_database_url):
    management = create_engine(test_database_url)
    schema = f"signup_test_{uuid4().hex}"
    with management.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    engine = create_engine(test_database_url, connect_args={"options": f"-c search_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with management.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        management.dispose()


@pytest.mark.parametrize("legacy", [None, "unique", "identity", "partial", "missing", "constant_id"])
def test_postgres_users_revision_preserves_legacy_data(postgres, legacy):
    if legacy:
        upgrade_database(postgres, "20261108_01")
        identifier = {
            "identity": "INTEGER GENERATED ALWAYS AS IDENTITY",
            "constant_id": "INTEGER DEFAULT 7",
        }.get(legacy, "SERIAL")
        with postgres.begin() as connection:
            connection.execute(text(
                f"CREATE TABLE users (id {identifier} PRIMARY KEY, username VARCHAR(50) NOT NULL, "
                "hashed_password VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL)"
            ))
            if legacy in {"unique", "identity", "constant_id"}:
                connection.execute(text("CREATE UNIQUE INDEX unique_users ON users (username)"))
            elif legacy == "partial":
                connection.execute(text("CREATE UNIQUE INDEX partial_users ON users (username) WHERE role = 'employee'"))
            connection.execute(text(
                "INSERT INTO users (username, hashed_password, role) VALUES ('existing', 'fixture', 'admin')"
            ))
    problem = {"partial": "username requires", "missing": "username requires", "constant_id": "automatically generated integer"}.get(legacy)
    if problem:
        with pytest.raises(RuntimeError, match=problem):
            upgrade_database(postgres)
    else:
        upgrade_database(postgres)
        assert any(index["unique"] and index["column_names"] == ["username"] for index in inspect(postgres).get_indexes("users"))
    with postgres.connect() as connection:
        version = "20261108_01" if problem else "20261115_02"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == version
        assert connection.execute(select(User.username, User.hashed_password, User.role)).all() == (
            [("existing", "fixture", "admin")] if legacy else []
        )


def test_simultaneous_registrations_store_exactly_one_employee(postgres, monkeypatch):
    upgrade_database(postgres)
    sessions = sessionmaker(bind=postgres)

    def db():
        with sessions() as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_db, db)
    monkeypatch.setattr(settings, "REGISTRATION_ENABLED", True)
    monkeypatch.setattr(settings, "REGISTRATION_REQUESTS_PER_MINUTE", 5)
    monkeypatch.setattr(app, "state", State({"auth_limiter": AuthRateLimiter()}))
    original_hash = auth.hash_password
    ready = Barrier(2)

    def synchronised_hash(password):
        # Both requests have now passed the username pre-check.
        ready.wait(timeout=10)
        return original_hash(password)

    monkeypatch.setattr(auth, "hash_password", synchronised_hash)
    credentials = {"username": "duplicate_race", "password": "Concurrent-fixture-42!"}

    def register():
        with TestClient(app) as client:
            return client.post("/auth/register", json=credentials)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: register(), range(2)))
    assert sorted(response.status_code for response in results) == [201, 409]
    conflict = next(response for response in results if response.status_code == 409)
    assert conflict.json() == {"detail": "Username already exists"}
    with sessions() as db_session:
        user = db_session.scalars(select(User)).one()
        assert (user.username, user.role) == ("duplicate_race", "employee")
        assert verify_password(credentials["password"], user.hashed_password)


def test_demo_seed_rolls_back_flushed_records_and_can_be_repeated(postgres, monkeypatch):
    upgrade_database(postgres)
    sessions = sessionmaker(bind=postgres)
    with sessions.begin() as db:
        db.add(User(username="seed_admin", hashed_password="test-fixture", role="admin"))
        db.add(Product(name="Keep", category="Existing", price=1, quantity=9, min_stock_level=1))
    monkeypatch.setattr(cli, "engine", postgres)
    original = cli.record_transaction
    calls = 0

    def fail_after_second_savepoint(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated failure after the transaction savepoint")
        return result

    monkeypatch.setattr(cli, "record_transaction", fail_after_second_savepoint)
    with pytest.raises(RuntimeError, match="simulated failure"):
        cli.seed_demo("seed_admin")
    with sessions() as db:
        assert db.execute(select(Product.name, Product.quantity)).all() == [("Keep", 9)]
        assert not db.scalars(select(AuditLog)).all()
        assert not db.scalars(select(InventoryTransaction)).all()

    monkeypatch.setattr(cli, "record_transaction", original)
    cli.seed_demo("seed_admin")
    cli.seed_demo("seed_admin")
    with sessions() as db:
        products = dict(db.execute(select(Product.name, Product.quantity)).all())
        assert products == {
            "Keep": 9, "[Demo] USB-C Dock": 6, "[Demo] Travel Charger": 24, "[Demo] Display Adapter": 0,
        }
        assert len(db.scalars(select(InventoryTransaction)).all()) == 3
        assert len(db.scalars(select(AuditLog)).all()) == 6


def test_production_tls_checks_ca_and_hostname_on_a_live_socket(test_database_url):
    root = environ.get("ELECTROSTOCK_TEST_CA")
    wrong_root = environ.get("ELECTROSTOCK_TEST_WRONG_CA")
    if not root or not wrong_root:
        pytest.skip("Set both CA paths for a disposable PostgreSQL server with a localhost-only certificate.")

    def connect(host, ca):
        url = test_database_url.set(host=host)
        config = Settings(
            _env_file=None, APP_ENV="production", DATABASE_URL=url.render_as_string(hide_password=False),
            DATABASE_SSL_ROOT_CERT=ca, FRONTEND_ORIGIN="https://inventory.example.com",
            JWT_SECRET_KEY="32a1282e1f80456bf41db4469ad8a9a6698f35287b3111cc442bd3bd",
        )
        engine = create_engine(config.connection_url(), connect_args={"connect_timeout": 5})
        try:
            with engine.connect() as connection:
                return connection.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")).scalar_one()
        finally:
            engine.dispose()

    assert connect("localhost", root) is True
    with pytest.raises(OperationalError, match="does not match host name"):
        connect("127.0.0.1", root)
    with pytest.raises(OperationalError, match="certificate verify failed"):
        connect("localhost", wrong_root)
