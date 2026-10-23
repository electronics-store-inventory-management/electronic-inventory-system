import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.product import Product
from app.services.report_service import generate_report

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


def create_test_product(db, name, quantity, min_stock_level=0):
    product = Product(
        name=name,
        category="Accessories",
        price=1000.00,
        quantity=quantity,
        min_stock_level=min_stock_level,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


# TC-Report-01.1
def test_product_below_minimum_is_low_stock(db):
    create_test_product(db, name="Low Item", quantity=2, min_stock_level=10)

    report = generate_report(db)

    low_stock = report.low_stock

    assert len(low_stock) == 1
    assert low_stock[0].name == "Low Item"


# TC-Report-01.2
def test_product_exactly_at_minimum_is_not_low(db):
    create_test_product(db, name="At Min Item", quantity=10, min_stock_level=10)

    report = generate_report(db)

    assert len(report.low_stock) == 0


# TC-Report-01.3
def test_product_with_no_threshold_never_low(db):
    create_test_product(db, name="No Threshold Item", quantity=0, min_stock_level=0)

    report = generate_report(db)

    assert len(report.low_stock) == 0


# TC-Report-01.4
def test_empty_inventory_gives_empty_lists(db):
    report = generate_report(db)

    assert report.products == []
    assert report.low_stock == []
