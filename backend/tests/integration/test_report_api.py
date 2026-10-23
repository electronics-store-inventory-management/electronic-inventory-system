from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.main import app
from app.models.product import Product
from app.routers.reports import get_db

from app.core.auth import ADMIN_HEADERS, EMPLOYEE_HEADERS

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


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def setup_database():
    Base.metadata.create_all(bind=engine)


def teardown_database():
    Base.metadata.drop_all(bind=engine)


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
    setup_database()

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

    teardown_database()


# TC-Report-01.2
def test_report_reflects_a_sale():
    setup_database()

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

    teardown_database()


# TC-Report-01.3
def test_empty_inventory_returns_200():
    setup_database()

    response = client.get("/reports/", headers=ADMIN_HEADERS)

    assert response.status_code == 200

    data = response.json()
    assert data["products"] == []
    assert data["low_stock"] == []

    teardown_database()


# TC-Report-01.4
def test_employee_gets_403():
    setup_database()

    response = client.get("/reports/", headers=EMPLOYEE_HEADERS)

    assert response.status_code == 403

    teardown_database()


# TC-Report-01.5
def test_no_login_gets_401():
    setup_database()

    response = client.get("/reports/")

    assert response.status_code == 401

    teardown_database()
