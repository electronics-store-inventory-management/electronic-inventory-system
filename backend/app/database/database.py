from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker, declarative_base


class Settings(BaseSettings):
    DATABASE_USER: str = ""
    DATABASE_PASSWORD: str = ""
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "electronics_store_db"
    DATABASE_URL: str | None = None
    JWT_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

if settings.DATABASE_URL:
    DATABASE_URL = make_url(settings.DATABASE_URL)
else:
    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg2",
        username=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        database=settings.DATABASE_NAME,
    )

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()