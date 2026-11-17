import re
from ipaddress import ip_network
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import declarative_base, sessionmaker

PLACEHOLDER_SIGNING_KEY = re.compile(
    r"replace(?:with|me)|change(?:me|this|inproduction)|placeholder|default|"
    r"example|sample|development|testonly|notforproduction|donotuse|"
    r"your(?:jwt|secret|key|random)|randomsecretatleast|insecure"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    APP_ENV: Literal["development", "production"] = "development"
    DATABASE_SSL_ROOT_CERT: str = ""
    DATABASE_USER: str = ""
    DATABASE_PASSWORD: str = ""
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "electronics_store_db"
    DATABASE_URL: str | None = None
    JWT_SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=60)
    FRONTEND_ORIGIN: str = Field(
        default="http://localhost:5173",
        validation_alias=AliasChoices("FRONTEND_ORIGIN", "FRONTEND_URL"),
    )
    REGISTRATION_ENABLED: bool | None = None
    AUTH_TRUSTED_PROXY_NETWORKS: str = ""
    LOGIN_REQUESTS_PER_MINUTE: int = Field(default=12, ge=1, le=120)
    REGISTRATION_REQUESTS_PER_MINUTE: int = Field(default=5, ge=1, le=60)

    @model_validator(mode="after")
    def validate_deployment(self):
        try:
            origin = urlsplit(self.FRONTEND_ORIGIN)
            valid_origin = (
                origin.scheme in {"http", "https"} and bool(origin.hostname)
                and origin.username is None and origin.password is None
                and not (origin.path or origin.query or origin.fragment)
                and "*" not in self.FRONTEND_ORIGIN
            )
            _ = origin.port
        except ValueError:
            valid_origin = False
        if not valid_origin:
            raise ValueError("FRONTEND_ORIGIN must be a single HTTP(S) origin without a trailing slash")
        self.trusted_proxy_networks()
        if self.REGISTRATION_ENABLED is None:
            self.REGISTRATION_ENABLED = self.APP_ENV == "development"
        if self.APP_ENV == "production":
            if origin.scheme != "https":
                raise ValueError("Production FRONTEND_ORIGIN must use HTTPS")
            if not self.DATABASE_URL:
                raise ValueError("Production DATABASE_URL is required")
            secret = self.JWT_SECRET_KEY.strip()
            normalized = re.sub(r"[^a-z0-9]", "", secret.lower())
            if (
                len(secret) < 32 or len(set(secret)) < 8 or secret.isdecimal()
                or PLACEHOLDER_SIGNING_KEY.search(normalized)
            ):
                raise PydanticCustomError(
                    "invalid_production_signing_key",
                    "Production JWT_SECRET_KEY must be a generated secret of at least 32 characters. Example and placeholder values are rejected.",
                )
        return self

    def trusted_proxy_networks(self):
        try:
            networks = tuple(
                ip_network(value.strip())
                for value in self.AUTH_TRUSTED_PROXY_NETWORKS.split(",")
                if value.strip()
            )
            if any(network.prefixlen == 0 for network in networks):
                raise ValueError
            return networks
        except ValueError:
            raise PydanticCustomError(
                "invalid_proxy_networks",
                "AUTH_TRUSTED_PROXY_NETWORKS must list explicit proxy IPs or CIDRs. Trust-all is forbidden.",
            ) from None

    def connection_url(self):
        if self.DATABASE_URL:
            try:
                url = make_url(self.DATABASE_URL)
                if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg2"}:
                    raise ValueError
                if not url.host or not url.database:
                    raise ValueError
            except (ArgumentError, ValueError):
                raise RuntimeError("DATABASE_URL must be a valid PostgreSQL URL with a host and database.") from None

            if self.APP_ENV == "production":
                # Query-string host or service options can change libpq's connection target.
                if set(url.query) - {"sslmode"} or url.query.get("sslmode", "verify-full") != "verify-full":
                    raise RuntimeError("Production DATABASE_URL may only specify sslmode=verify-full. Set the CA in DATABASE_SSL_ROOT_CERT.")
                if not self.DATABASE_SSL_ROOT_CERT or not Path(self.DATABASE_SSL_ROOT_CERT).is_file():
                    raise RuntimeError("Production DATABASE_SSL_ROOT_CERT must point to the provider's trusted CA bundle.")
                url = url.update_query_dict({
                    "sslmode": "verify-full",
                    "sslrootcert": str(Path(self.DATABASE_SSL_ROOT_CERT).resolve()),
                    "gssencmode": "disable",
                })
            return url.set(drivername="postgresql+psycopg2")
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            database=self.DATABASE_NAME,
        )


# Do not expose Settings validation input, which may include credentials.
try:
    settings = Settings()
except ValidationError as error:
    fields = ", ".join(
        item["msg"] if item["type"] in {"invalid_production_signing_key", "invalid_proxy_networks"}
        else ".".join(map(str, item["loc"])) or "deployment settings"
        for item in error.errors()
    )
    raise RuntimeError(f"Invalid configuration: {fields}. See backend/.env.example.") from None

DATABASE_URL = settings.connection_url()
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    hide_parameters=True,
    connect_args={"connect_timeout": 5},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
