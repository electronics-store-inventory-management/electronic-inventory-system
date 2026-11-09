from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.database.database import Base, engine
import app.models  # noqa: F401  registers all models with Base.metadata
from app.routers.audit_logs import router as audit_logs_router
from app.routers.auth import router as auth_router
from app.routers.product import router as product_router
from app.routers.reports import router as reports_router
from app.routers.suppliers import router as suppliers_router
from app.routers.transactions import router as transactions_router


try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass


app = FastAPI(
    title="Electronics Store Inventory Management System",
    version="1.0.0",
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


@app.get("/")
def root():
    return {
        "message": "Electronics Store Inventory Management System API"
    }
