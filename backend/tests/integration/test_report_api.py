from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.database.database import Base, get_db as db_get_db
from app.main import app
from app.models.product import Product
from app.routers.audit_logs import get_db as audit_get_db
from app.routers.product import get_db as product_get_db
from app.routers.reports import get_db as reports_get_db
from app.routers.suppliers import get_db as suppliers_get_db
from app.routers.transactions import get_db as transactions_get_db

from tests.auth_helpers import ADMIN_HEADERS, EMPLOYEE_HEADERS
from tests.test_users import seed_test_users

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


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


GET_DBS = (
    db_get_db,
    product_get_db,
    suppliers_get_db,
    transactions_get_db,
    reports_get_db,
    audit_get_db,
)


@pytest.fixture(autouse=True)
def _db_setup():
    saved = dict(app.dependency_overrides)

    for _get_db in GET_DBS:
        app.dependency_overrides[_get_db] = override_get_db

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_test_users(db)
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)

    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


client = TestClient(app)


def create_product_db(name, quantity, min_stock_level=0):
    session = TestingSessionLocal()
    product = Product(
        name=name,
        category="Accessories",
        price=1000.00,
        quantity=quantity,
        min_stock_level=min_stock_level,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    pid = product.id
    session.close()
    return pid


# TC-Report-01.1
def test_admin_gets_all_products_and_low_stock_list():
    create_product_db("Low Item", quantity=2, min_stock_level=10)
    create_product_db("At Min Item", quantity=10, min_stock_level=10)
    create_product_db("OK Item", quantity=50, min_stock_level=5)
    create_product_db("No Threshold", quantity=0, min_stock_level=0)

    response = client.get("/reports/", headers=ADMIN_HEADERS)

    assert response.status_code == 200

    data = response.json()
    assert len(data["products"]) == 4
    assert len(data["low_stock"]) == 1
    assert data["low_stock"][0]["name"] == "Low Item"


# TC-Report-01.2
def test_report_reflects_a_sale():
    product_id = create_product_db("Sale Item", quantity=20)

    client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "DEDUCT",
            "quantity": 5,
            "user_id": 2,
            "reference": "SALE-001",
        },
        headers=EMPLOYEE_HEADERS,
    )

    response = client.get("/reports/", headers=ADMIN_HEADERS)

    assert response.status_code == 200

    data = response.json()
    product = next(p for p in data["products"] if p["id"] == product_id)
    assert product["quantity"] == 15


# TC-Report-01.3
def test_empty_inventory_returns_200():
    response = client.get("/reports/", headers=ADMIN_HEADERS)

    assert response.status_code == 200

    data = response.json()
    assert data["products"] == []
    assert data["low_stock"] == []


# TC-Report-01.4
def test_employee_gets_403():
    response = client.get("/reports/", headers=EMPLOYEE_HEADERS)

    assert response.status_code == 403


# TC-Report-01.5
def test_no_login_gets_401():
    response = client.get("/reports/")

    assert response.status_code == 401
