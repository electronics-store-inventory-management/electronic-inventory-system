from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.models.product import Product
from app.models.transaction import InventoryTransaction
from app.schemas.transaction import InventoryTransactionCreate
from app.services.audit_service import log_audit


VALID_TYPES = {"ADD", "DEDUCT"}


def record_transaction(
    db: Session,
    transaction_data: InventoryTransactionCreate,
) -> InventoryTransaction:
    transaction_type = transaction_data.transaction_type

    if transaction_type not in VALID_TYPES:
        raise BadRequestError(
            f"Invalid transaction type '{transaction_type}'. Use 'ADD' or 'DEDUCT'."
        )

    if not transaction_data.reference or not transaction_data.reference.strip():
        raise BadRequestError("Reference is required")

    quantity = transaction_data.quantity

    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise BadRequestError("Quantity must be a whole number")

    if quantity <= 0:
        raise BadRequestError("Quantity must be greater than zero")

    product = db.query(Product).filter(Product.id == transaction_data.product_id).first()

    if product is None:
        raise NotFoundError("Product not found")

    if transaction_type == "DEDUCT" and product.quantity < quantity:
        raise BadRequestError("Insufficient stock")

    try:
        if transaction_type == "ADD":
            product.quantity += quantity
        else:
            product.quantity -= quantity

        transaction = InventoryTransaction(
            product_id=product.id,
            transaction_type=transaction_type,
            quantity=quantity,
            date=transaction_data.date or datetime.utcnow(),
            user_id=transaction_data.user_id,
            reference=transaction_data.reference.strip(),
        )
        db.add(transaction)
        db.flush()

        log_audit(
            db,
            user_id=transaction_data.user_id,
            action=f"inventory_{transaction_type.lower()}",
            entity="inventory_transaction",
            entity_id=transaction.id,
        )

        db.commit()
        db.refresh(transaction)

        return transaction
    except Exception:
        db.rollback()
        raise


def get_transactions(
    db: Session,
    product_id: int | None = None,
) -> list[InventoryTransaction]:
    query = db.query(InventoryTransaction)

    if product_id is not None:
        query = query.filter(InventoryTransaction.product_id == product_id)

    return query.order_by(InventoryTransaction.date.desc()).all()
