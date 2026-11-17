import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app import main
from app.database.database import Settings


@pytest.fixture
def production(monkeypatch):
    monkeypatch.delenv("REGISTRATION_ENABLED", raising=False)
    return {
        "_env_file": None,
        "APP_ENV": "production",
        "FRONTEND_ORIGIN": "https://inventory.example.com",
        "JWT_SECRET_KEY": "32a1282e1f80456bf41db4469ad8a9a6698f35287b3111cc442bd3bd",
        "DATABASE_URL": "postgres://user:fixture@db.example.com/inventory",
    }


def test_production_settings_require_explicit_configuration():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV="production", DATABASE_URL="", JWT_SECRET_KEY="", FRONTEND_ORIGIN="http://localhost:5173")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, FRONTEND_ORIGIN="*")


@pytest.mark.parametrize("key", [
    "", " " * 40, "default-secret-key-that-is-not-random",
    "REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS",
    "example-signing-key-that-is-not-random", "0123456789012345678901234567890123",
    "CHANGE_ME_TO_A_LONG_PRODUCTION_KEY", "x" * 40,
])
def test_production_rejects_unsafe_signing_keys(production, key):
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY") as error:
        Settings(**{**production, "JWT_SECRET_KEY": key})
    if key.strip():
        assert key not in str(error.value)


def test_invalid_production_key_stops_application_startup_without_exposing_configuration(production):
    env = {**os.environ, **{name: value for name, value in production.items() if name != "_env_file"}}
    env["JWT_SECRET_KEY"] = "change-this-local-fixture-before-production"
    result = subprocess.run(
        [sys.executable, "-B", "-c", "import app.main"], env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0
    assert "Production JWT_SECRET_KEY must be a generated secret" in result.stderr
    assert env["JWT_SECRET_KEY"] not in result.stderr
    assert env["DATABASE_URL"] not in result.stderr


def test_signup_requires_production_opt_in(production, monkeypatch):
    assert Settings(**production).REGISTRATION_ENABLED is False
    assert Settings(_env_file=None, APP_ENV="development", JWT_SECRET_KEY="local").REGISTRATION_ENABLED is True
    monkeypatch.setenv("REGISTRATION_ENABLED", "true")
    assert Settings(**production).REGISTRATION_ENABLED is True


def test_frontend_origin_prefers_documented_setting(monkeypatch):
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    assert Settings(_env_file=None, APP_ENV="development").FRONTEND_ORIGIN == "http://localhost:3000"
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://inventory.example.com")
    assert Settings(_env_file=None, APP_ENV="development").FRONTEND_ORIGIN == "https://inventory.example.com"


def test_cors_preflight_uses_configured_frontend_origin(production, tmp_path):
    env = {**os.environ, **{name: value for name, value in production.items() if name != "_env_file"}}
    ca_bundle = tmp_path / "provider-ca.pem"
    ca_bundle.touch()
    env["DATABASE_SSL_ROOT_CERT"] = str(ca_bundle)
    result = subprocess.run(
        [sys.executable, "-B", "-c", """
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
headers = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}
origin = "https://inventory.example.com"
allowed = client.options("/auth/login", headers={**headers, "Origin": origin})
assert allowed.status_code == 200
assert allowed.headers["access-control-allow-origin"] == origin

denied = client.options("/auth/login", headers={**headers, "Origin": "https://other.example.com"})
assert denied.status_code == 400
assert "access-control-allow-origin" not in denied.headers
"""],
        env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_provider_database_url_enforces_certificate_and_hostname_verification(production, tmp_path):
    ca_bundle = tmp_path / "provider-ca.pem"
    ca_bundle.touch()
    settings = Settings(**production, DATABASE_SSL_ROOT_CERT=str(ca_bundle))
    url = settings.connection_url()
    assert url.drivername == "postgresql+psycopg2"
    assert url.database == "inventory"
    assert url.host == "db.example.com"
    assert dict(url.query) == {"sslmode": "verify-full", "sslrootcert": str(ca_bundle), "gssencmode": "disable"}
    _, arguments = create_engine(url).dialect.create_connect_args(url)
    assert arguments["host"] == "db.example.com"
    assert arguments["sslmode"] == "verify-full"
    assert arguments["sslrootcert"] == str(ca_bundle)


@pytest.mark.parametrize("options", [
    "?sslmode=require", "?sslmode=verify-ca", "?sslmode=disable",
    "?sslmode=verify-full&sslmode=require", "?host=another.example.com",
    "?sslrootcert=another.pem", "?gssencmode=prefer",
])
def test_production_rejects_tls_downgrades_and_url_overrides(production, options):
    url = production["DATABASE_URL"]
    with pytest.raises(RuntimeError, match="verify-full"):
        Settings(**{**production, "DATABASE_URL": url + options}).connection_url()


def test_production_requires_ca_file(production, tmp_path):
    with pytest.raises(RuntimeError, match="DATABASE_SSL_ROOT_CERT"):
        Settings(**production, DATABASE_SSL_ROOT_CERT=str(tmp_path / "missing.pem")).connection_url()


@pytest.mark.parametrize("networks", ["*", "0.0.0.0/0", "::/0", "proxy.example.com"])
def test_trust_all_or_unresolved_proxy_configuration_is_rejected(production, networks):
    with pytest.raises(ValidationError, match="AUTH_TRUSTED_PROXY_NETWORKS"):
        Settings(**production, AUTH_TRUSTED_PROXY_NETWORKS=networks)


def test_health_reports_database_connectivity_without_details(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(main, "engine", engine)
    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        def unavailable():
            raise OperationalError("private dsn", None, RuntimeError("private connection failure"))

        monkeypatch.setattr(engine, "connect", unavailable)
        response = client.get("/health")
        assert response.status_code == 503
        assert "private" not in response.text
    engine.dispose()
