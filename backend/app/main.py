
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.routers.audit_logs import router as audit_logs_router
from app.routers.auth import router as auth_router
from app.routers.product import router as product_router
from app.routers.reports import router as reports_router
from app.routers.suppliers import router as suppliers_router
from app.routers.transactions import router as transactions_router
from app.routers.availability import router as availability_router
from app.routers.availability import monitor_once


async def availability_monitor():
    while True:
        try:
            await asyncio.to_thread(monitor_once)
        except Exception:
            logging.exception("Availability monitor sample failed")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(availability_monitor())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Electronics Store Inventory Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


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
