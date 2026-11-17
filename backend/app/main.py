import asyncio
import logging
import os
from contextlib import asynccontextmanager

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.auth_limits import AuthBodyLimit, AuthRateLimiter
from app.core.errors import AppError
from app.database.database import engine, settings
from app.routers.audit_logs import router as audit_logs_router
from app.routers.auth import router as auth_router
from app.routers.availability import monitor_once, router as availability_router
from app.routers.product import router as product_router
from app.routers.reports import router as reports_router
from app.routers.suppliers import router as suppliers_router
from app.routers.transactions import router as transactions_router


async def availability_monitor():
    while True:
        try:
            await asyncio.to_thread(monitor_once)
        except Exception:
            logging.exception("Availability monitor sample failed")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor_task = asyncio.create_task(availability_monitor())
    try:
        yield
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Electronics Store Inventory Management System",
    version="1.0.0",
    debug=False,
    docs_url=None if settings.APP_ENV == "production" else "/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/redoc",
    openapi_url=None if settings.APP_ENV == "production" else "/openapi.json",
    lifespan=lifespan,
)
app.state.auth_limiter = AuthRateLimiter(trusted_proxies=settings.trusted_proxy_networks())

app.add_middleware(AuthBodyLimit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    expose_headers=["Retry-After"],
)


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(request: Request, exc: RequestValidationError):
    # Do not echo submitted values: validation errors may contain passwords,
    # tokens, supplier contacts, or inventory data.
    errors = [
        {
            "loc": error.get("loc", ()) if error.get("type") != "extra_forbidden" else ("body",),
            "msg": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(OperationalError)
def database_unavailable(request: Request, exc: OperationalError):
    return JSONResponse(status_code=503, content={"detail": "Database is temporarily unavailable."})


@app.exception_handler(SQLAlchemyError)
def database_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "Unable to complete the database operation."})


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(product_router)
app.include_router(suppliers_router)
app.include_router(transactions_router)
app.include_router(reports_router)
app.include_router(audit_logs_router)
app.include_router(auth_router)
app.include_router(availability_router)


@app.get("/")
def root():
    return {
        "message": "Electronics Store Inventory Management System API"
    }
