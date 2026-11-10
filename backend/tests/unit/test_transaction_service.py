import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import BadRequestError
from app.database.database import Base
from app.models.audit_log import AuditLog
from app.models.product import Product
from app.models.transaction import InventoryTransaction
from app.schemas.transaction import InventoryTransactionCreate
from app.services.transaction_service import record_transaction

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_test_product(db, name="Test Product", quantity=100):
    product = Product(name=name, category="Accessories", price=1000.00, quantity=quantity)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


# TC-Transaction-01.1
def test_record_add_and_deduct_transaction(db):
    product = create_test_product(db, quantity=100)

    add_tx = record_transaction(
        db,
        InventoryTransactionCreate(
            product_id=product.id,
            transaction_type="ADD",
            quantity=10,
            user_id=1,
            reference="RESTOCK-001",
        ),
    )

    assert add_tx.id is not None
    assert add_tx.transaction_type == "ADD"
    assert add_tx.quantity == 10
    assert add_tx.user_id == 1
    assert add_tx.reference == "RESTOCK-001"

    assert product.quantity == 110

    deduct_tx = record_transaction(
        db,
        InventoryTransactionCreate(
            product_id=product.id,
            transaction_type="DEDUCT",
            quantity=4,
            user_id=2,
            reference="SALE-001",
        ),
    )

    assert deduct_tx.id is not None
    assert deduct_tx.transaction_type == "DEDUCT"
    assert deduct_tx.quantity == 4
    assert deduct_tx.user_id == 2
    assert deduct_tx.reference == "SALE-001"

    assert product.quantity == 106

    # audit rows created together with transactions
    audit_rows = db.query(AuditLog).all()
    assert len(audit_rows) == 2
    assert all(row.user_id in (1, 2) for row in audit_rows)
    assert all(row.timestamp is not None for row in audit_rows)


# TC-Transaction-01.2
def test_deduct_more_than_available_stock_is_rejected_without_side_effects(db):
    product = create_test_product(db, quantity=5)

    with pytest.raises(BadRequestError, match="^Insufficient stock$"):
        record_transaction(
            db,
            InventoryTransactionCreate(
                product_id=product.id,
                transaction_type="DEDUCT",
                quantity=6,
                user_id=2,
                reference="SALE-OVERSTOCK",
            ),
        )

    assert product.quantity == 5
    assert db.query(InventoryTransaction).count() == 0
    assert db.query(AuditLog).count() == 0


# TC-Transaction-01.2
def test_invalid_quantity_rejected(db):
    product = create_test_product(db)

    for bad_quantity in [0, -1, "abc", None]:
        with pytest.raises(Exception):
            record_transaction(
                db,
                InventoryTransactionCreate(
                    product_id=product.id,
                    transaction_type="ADD",
                    quantity=bad_quantity,
                    user_id=1,
                    reference="REF",
                ),
            )


# TC-Transaction-01.3
def test_invalid_type_or_reference_rejected(db):
    product = create_test_product(db)

    with pytest.raises(Exception):
        record_transaction(
            db,
            InventoryTransactionCreate(
                product_id=product.id,
                transaction_type="INVALID",
                quantity=5,
                user_id=1,
                reference="REF",
            ),
        )

    with pytest.raises(Exception):
        record_transaction(
            db,
            InventoryTransactionCreate(
                product_id=product.id,
                transaction_type="ADD",
                quantity=5,
                user_id=1,
                reference="",
            ),
        )


# TC-Transaction-01.4
def test_unknown_product_not_found(db):
    with pytest.raises(Exception):
        record_transaction(
            db,
            InventoryTransactionCreate(
                product_id=9999,
                transaction_type="ADD",
                quantity=5,
                user_id=1,
                reference="REF",
            ),
        )


# TC-Transaction-01.5
def test_rollback_removes_transaction_and_audit_row(db):
    product = create_test_product(db, quantity=100)

    tx = record_transaction(
        db,
        InventoryTransactionCreate(
            product_id=product.id,
            transaction_type="ADD",
            quantity=10,
            user_id=1,
            reference="REF",
        ),
    )

    assert db.query(InventoryTransaction).filter(InventoryTransaction.id == tx.id).first() is not None
    assert db.query(AuditLog).count() == 1
