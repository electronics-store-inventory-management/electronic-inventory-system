from datetime import datetime
from hashlib import sha256

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.models.product import Product
from app.models.transaction import InventoryTransaction
from app.schemas.transaction import InventoryTransactionCreate
from app.services.audit_service import log_audit


VALID_TYPES = {"ADD", "DEDUCT", "SET"}


def _matches_request(existing: InventoryTransaction, data: InventoryTransactionCreate) -> bool:
    return (
        existing.product_id == data.product_id
        and existing.transaction_type == data.transaction_type
        and existing.quantity == data.quantity
        and existing.reference == data.reference.strip()
    )


def record_transaction(
    db: Session,
    transaction_data: InventoryTransactionCreate,
    authenticated_user_id: int | None = None,
    idempotency_key: str | None = None,
) -> InventoryTransaction:
    transaction_type = transaction_data.transaction_type
    if transaction_type not in VALID_TYPES:
        raise BadRequestError("Invalid transaction type. Use 'ADD', 'DEDUCT', or 'SET'.")
    if not transaction_data.reference or not transaction_data.reference.strip():
        raise BadRequestError("Reference is required")

    quantity = transaction_data.quantity
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise BadRequestError("Quantity must be a whole number")
    if quantity < 0 or (quantity == 0 and transaction_type != "SET"):
        raise BadRequestError("Quantity must be greater than zero, except for SET adjustments")

    user_id = (
        authenticated_user_id
        if authenticated_user_id is not None
        else transaction_data.user_id
    )
    key = idempotency_key if idempotency_key is not None else transaction_data.idempotency_key
    if key is not None:
        key = key.strip()
        if not key:
            raise BadRequestError("Idempotency key cannot be blank")
        key = f"user:{user_id}:{sha256(key.encode()).hexdigest()}"
        existing = db.query(InventoryTransaction).filter_by(idempotency_key=key).first()
        if existing is not None:
            if _matches_request(existing, transaction_data):
                return existing
            raise ConflictError("Idempotency key was already used for a different transaction")

    try:
        if transaction_type in {"ADD", "DEDUCT"}:
            delta = quantity if transaction_type == "ADD" else -quantity
            conditions = [Product.id == transaction_data.product_id]
            if transaction_type == "DEDUCT":
                conditions.append(Product.quantity >= quantity)
            result = db.execute(
                update(Product)
                .where(*conditions)
                .values(quantity=Product.quantity + delta)
                .execution_options(synchronize_session="fetch")
            )
            if result.rowcount != 1:
                exists = db.query(Product.id).filter(Product.id == transaction_data.product_id).first()
                if exists is None:
                    raise NotFoundError("Product not found")
                raise BadRequestError("Insufficient stock")
            product_id = transaction_data.product_id
        else:
            # SELECT FOR UPDATE serializes SET adjustments with all stock operations.
            product = (
                db.query(Product)
                .filter(Product.id == transaction_data.product_id)
                .with_for_update()
                .first()
            )
            if product is None:
                raise NotFoundError("Product not found")
            product.quantity = quantity
            product_id = product.id

        transaction = InventoryTransaction(
            product_id=product_id,
            transaction_type=transaction_type,
            quantity=quantity,
            date=transaction_data.date or datetime.utcnow(),
            user_id=user_id,
            reference=transaction_data.reference.strip(),
            idempotency_key=key,
        )
        db.add(transaction)
        db.flush()
        log_audit(
            db,
            user_id=user_id,
            action=f"inventory_{transaction_type.lower()}",
            entity="inventory_transaction",
            entity_id=transaction.id,
        )
        db.commit()
        db.refresh(transaction)
        return transaction
    except IntegrityError as exc:
        db.rollback()
        if key is not None:
            existing = db.query(InventoryTransaction).filter_by(idempotency_key=key).first()
            if existing is not None:
                if _matches_request(existing, transaction_data):
                    return existing
                raise ConflictError("Idempotency key was already used for a different transaction") from exc
        raise
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
