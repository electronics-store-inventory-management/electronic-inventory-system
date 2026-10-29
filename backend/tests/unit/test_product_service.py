from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product_service import (
    create_product,
    get_product,
    get_products,
    update_product,
    delete_product,
)


# Use a separate in-memory database for unit tests.
# This keeps tests isolated from the real PostgreSQL database.
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


def create_test_product(
    db,
    name="Test Laptop",
    category="Laptop",
    price=50000.00,
    quantity=10,
):
    product_data = ProductCreate(
        name=name,
        category=category,
        price=Decimal(str(price)),
        quantity=quantity,
    )

    return create_product(db, product_data)


def test_create_product(db):
    product = create_test_product(db)

    assert product.id is not None
    assert product.name == "Test Laptop"
    assert product.category == "Laptop"
    assert product.price == Decimal("50000.00")
    assert product.quantity == 10
    assert product.min_stock_level == 0


def test_create_and_update_product_minimum_stock_level(db):
    """Verify the service persists a threshold on creation and updates it later."""
    product = create_product(
        db,
        ProductCreate(
            name="Threshold Laptop",
            category="Laptop",
            price=Decimal("50000.00"),
            quantity=10,
            min_stock_level=4,
        ),
    )
    # Save the pre-update value because SQLAlchemy refreshes this same ORM object.
    original_minimum = product.min_stock_level

    updated = update_product(
        db,
        product.id,
        ProductUpdate(min_stock_level=6),
    )

    assert original_minimum == 4
    assert updated.min_stock_level == 6


@pytest.mark.parametrize("field", ["quantity", "min_stock_level"])
def test_product_schema_rejects_negative_stock_values(field):
    """Verify request models reject negative quantity and threshold values."""
    values = {
        "name": "Invalid Product",
        "category": "Laptop",
        "price": Decimal("100.00"),
        "quantity": 1,
        "min_stock_level": 1,
    }
    values[field] = -1

    with pytest.raises(Exception):
        ProductCreate(**values)

    with pytest.raises(Exception):
        ProductUpdate(**{field: -1})


def test_get_product(db):
    product = create_test_product(db)

    result = get_product(db, product.id)

    assert result is not None
    assert result.id == product.id
    assert result.name == "Test Laptop"


def test_get_product_not_found(db):
    result = get_product(db, 9999)

    assert result is None


def test_search_product_by_name(db):
    create_test_product(
        db,
        name="Sony Headphones",
        category="Headphones",
    )

    create_test_product(
        db,
        name="Dell Laptop",
        category="Laptop",
    )

    results = get_products(
        db,
        name="Sony",
    )

    assert len(results) == 1
    assert results[0].name == "Sony Headphones"


def test_search_product_by_category(db):
    create_test_product(
        db,
        name="Sony Headphones",
        category="Headphones",
    )

    create_test_product(
        db,
        name="Dell Laptop",
        category="Laptop",
    )

    results = get_products(
        db,
        category="Headphones",
    )

    assert len(results) == 1
    assert results[0].category == "Headphones"


def test_search_product_by_id(db):
    product = create_test_product(db)

    results = get_products(
        db,
        product_id=product.id,
    )

    assert len(results) == 1
    assert results[0].id == product.id


def test_update_product(db):
    product = create_test_product(db)

    update_data = ProductUpdate(
        price=Decimal("45000.00"),
        quantity=15,
    )

    updated_product = update_product(
        db,
        product.id,
        update_data,
    )

    assert updated_product is not None
    assert updated_product.price == Decimal("45000.00")
    assert updated_product.quantity == 15


def test_update_product_not_found(db):
    update_data = ProductUpdate(
        quantity=20,
    )

    result = update_product(
        db,
        9999,
        update_data,
    )

    assert result is None


def test_delete_product(db):
    product = create_test_product(db)

    deleted_product = delete_product(
        db,
        product.id,
    )

    assert deleted_product is not None
    assert deleted_product.id == product.id

    result = get_product(
        db,
        product.id,
    )

    assert result is None


def test_delete_product_not_found(db):
    result = delete_product(
        db,
        9999,
    )

    assert result is None
