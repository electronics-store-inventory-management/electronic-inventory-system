import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.product import Product
from app.models.supplier import ProductSupplier, Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.supplier_service import (
    create_supplier,
    get_product_suppliers,
    get_supplier,
    get_suppliers,
    link_product_supplier,
    update_supplier,
)

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


def create_test_supplier(db, name="Test Supplier", email="test@example.com"):
    supplier_data = SupplierCreate(name=name, email=email)
    return create_supplier(db, supplier_data, 1)


def create_test_product(db, name="Test Product", quantity=10):
    product = Product(name=name, category="Accessories", price=1000.00, quantity=quantity)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


# TC-Supplier-01.1
def test_valid_create_stores_supplier(db):
    supplier = create_test_supplier(db)

    assert supplier.id is not None
    assert supplier.name == "Test Supplier"
    assert supplier.email == "test@example.com"


# TC-Supplier-01.2
def test_blank_name_rejected(db):
    with pytest.raises(Exception):
        SupplierCreate(name="", email="test@example.com")


# TC-Supplier-01.3
def test_invalid_email_rejected(db):
    with pytest.raises(Exception):
        SupplierCreate(name="Test Supplier", email="not-an-email")


# TC-Supplier-01.4
def test_duplicate_name_ignoring_case_is_conflict(db):
    create_test_supplier(db, name="ACME Corp", email="acme@example.com")

    with pytest.raises(Exception):
        create_supplier(
            db,
            SupplierCreate(name="acme corp", email="other@example.com"),
            1,
        )


# TC-Supplier-01.5
def test_update_changes_fields(db):
    supplier = create_test_supplier(db)

    update_data = SupplierUpdate(name="New Name", email="new@example.com")

    updated = update_supplier(db, supplier.id, update_data, 1)

    assert updated is not None
    assert updated.name == "New Name"
    assert updated.email == "new@example.com"


# TC-Supplier-01.6
def test_update_missing_supplier_not_found(db):
    update_data = SupplierUpdate(name="New Name")

    result = update_supplier(db, 9999, update_data, 1)

    assert result is None


# TC-Supplier-02.1
def test_link_and_list_product_suppliers(db):
    product = create_test_product(db)
    supplier = create_test_supplier(db)

    link = link_product_supplier(db, product.id, supplier.id)

    assert link is not None
    assert link.product_id == product.id
    assert link.supplier_id == supplier.id

    links = get_product_suppliers(db, product.id)

    assert len(links) == 1
    assert links[0].supplier_id == supplier.id


# TC-Supplier-02.2
def test_product_with_no_supplier_returns_empty(db):
    product = create_test_product(db)

    links = get_product_suppliers(db, product.id)

    assert links == []


# TC-Supplier-02.3
def test_duplicate_link_is_conflict(db):
    product = create_test_product(db)
    supplier = create_test_supplier(db)

    link_product_supplier(db, product.id, supplier.id)

    with pytest.raises(Exception):
        link_product_supplier(db, product.id, supplier.id)


# TC-Supplier-02.4
def test_unknown_product_or_supplier_not_found(db):
    supplier = create_test_supplier(db)

    with pytest.raises(Exception):
        link_product_supplier(db, 9999, supplier.id)

    product = create_test_product(db)

    with pytest.raises(Exception):
        link_product_supplier(db, product.id, 9999)
