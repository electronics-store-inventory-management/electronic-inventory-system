from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import SessionLocal
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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if (
        transaction_data.transaction_type in {"ADD", "SET"}
        and current_user.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: only administrators can change stock levels",
        )

    return record_transaction(
        db,
        transaction_data,
        authenticated_user_id=current_user["id"],
        idempotency_key=idempotency_key,
    )


@router.get(
    "/",
    response_model=list[InventoryTransactionResponse],
)
def list_transactions(
    product_id: int | None = Query(default=None, gt=0),
    limit: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_transactions(db, product_id=product_id, limit=limit)
