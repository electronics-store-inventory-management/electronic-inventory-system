from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.database.database import SessionLocal
from app.models.product import Product
from app.models.transaction import InventoryTransaction
from app.schemas.transaction import InventoryTransactionCreate, InventoryTransactionResponse
from app.services.transaction_service import get_transactions, record_transaction

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=InventoryTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_transaction(
    transaction_data: InventoryTransactionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if (
        transaction_data.transaction_type == "ADD"
        and current_user.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: only administrators can restock",
        )

    return record_transaction(db, transaction_data)


@router.get(
    "/",
    response_model=list[InventoryTransactionResponse],
)
def list_transactions(
    product_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_transactions(db, product_id=product_id)
