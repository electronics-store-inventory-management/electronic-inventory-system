from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.database.database import SessionLocal
from app.schemas.report import InventoryReport
from app.services.report_service import generate_report

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get(
    "/",
    response_model=InventoryReport,
)
def get_inventory_report(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    return generate_report(db)
