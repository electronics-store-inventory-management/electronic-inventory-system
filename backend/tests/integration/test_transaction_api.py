from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.main import app
from app.models.product import Product
from app.routers.transactions import get_db

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


def create_product_db(name="Widget", quantity=100):
    session = TestingSessionLocal()
    product = Product(name=name, category="Gadgets", price=10.00, quantity=quantity)
    session.add(product)
    session.commit()
    session.refresh(product)
    pid = product.id
    session.close()
    return pid


# TC-Transaction-01.1
def test_restock_shows_up_in_transactions():
    setup_database()

    product_id = create_product_db(quantity=100)

    response = client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "ADD",
            "quantity": 20,
            "user_id": 1,
            "reference": "RESTOCK-001",
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201

    response = client.get("/transactions/", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["transaction_type"] == "ADD"
    assert data[0]["quantity"] == 20
    assert data[0]["user_id"] == 1
    assert data[0]["reference"] == "RESTOCK-001"

    teardown_database()


# TC-Transaction-01.2
def test_sale_creates_deduct_row():
    setup_database()

    product_id = create_product_db(quantity=100)

    response = client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "DEDUCT",
            "quantity": 4,
            "user_id": 2,
            "reference": "SALE-001",
        },
        headers=EMPLOYEE_HEADERS,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["transaction_type"] == "DEDUCT"
    assert data["quantity"] == 4

    teardown_database()


# TC-Transaction-01.3
def test_sale_larger_than_stock_no_row_stock_unchanged():
    setup_database()

    product_id = create_product_db(quantity=5)

    response = client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "DEDUCT",
            "quantity": 10,
            "user_id": 2,
            "reference": "SALE-001",
        },
        headers=EMPLOYEE_HEADERS,
    )

    assert response.status_code == 400

    product_response = client.get(f"/products/{product_id}", headers=ADMIN_HEADERS)
    assert product_response.json()["quantity"] == 5

    transactions = client.get("/transactions/", headers=ADMIN_HEADERS).json()
    assert len(transactions) == 0

    teardown_database()


# TC-Transaction-01.4
def test_filtering_by_product_and_newest_first():
    setup_database()

    product_a = create_product_db("Product A", quantity=100)
    product_b = create_product_db("Product B", quantity=100)

    client.post(
        "/transactions/",
        json={
            "product_id": product_a,
            "transaction_type": "ADD",
            "quantity": 10,
            "user_id": 1,
            "reference": "FIRST",
        },
        headers=ADMIN_HEADERS,
    )

    client.post(
        "/transactions/",
        json={
            "product_id": product_b,
            "transaction_type": "ADD",
            "quantity": 20,
            "user_id": 1,
            "reference": "SECOND",
        },
        headers=ADMIN_HEADERS,
    )

    response = client.get(
        f"/transactions/?product_id={product_a}",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["reference"] == "FIRST"

    response = client.get("/transactions/", headers=ADMIN_HEADERS)
    data = response.json()
    assert len(data) == 2
    assert data[0]["reference"] == "SECOND"
    assert data[1]["reference"] == "FIRST"

    teardown_database()


# TC-Transaction-01.5
def test_without_login_401():
    setup_database()

    response = client.post(
        "/transactions/",
        json={
            "product_id": 1,
            "transaction_type": "ADD",
            "quantity": 5,
            "user_id": 1,
            "reference": "REF",
        },
    )
    assert response.status_code == 401

    response = client.get("/transactions/")
    assert response.status_code == 401

    teardown_database()


# TC-Transaction-01.6
def test_post_not_allowed_for_employee_restock():
    setup_database()

    product_id = create_product_db(quantity=100)

    response = client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "ADD",
            "quantity": 5,
            "user_id": 2,
            "reference": "RESTOCK",
        },
        headers=EMPLOYEE_HEADERS,
    )

    assert response.status_code == 403

    teardown_database()
