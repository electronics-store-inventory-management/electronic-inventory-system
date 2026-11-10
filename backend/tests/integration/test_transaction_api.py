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
    product_response = client.get(
        f"/products/{product_id}",
        headers=ADMIN_HEADERS,
    )
    assert product_response.status_code == 200
    assert product_response.json()["quantity"] == 120
    data = response.json()
    assert len(data) == 1
    assert data[0]["transaction_type"] == "ADD"
    assert data[0]["quantity"] == 20
    assert data[0]["user_id"] == 1
    assert data[0]["reference"] == "RESTOCK-001"
    assert client.get(
        f"/products/{product_id}", headers=ADMIN_HEADERS
    ).json()["quantity"] == 120


# TC-Transaction-01.2
def test_sale_creates_deduct_row():
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
    assert data["user_id"] == 2
    assert client.get(
        f"/products/{product_id}", headers=ADMIN_HEADERS
    ).json()["quantity"] == 96


def test_authenticated_user_overrides_body_user_id():
    product_id = create_product_db(quantity=20)
    response = client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "DEDUCT",
            "quantity": 1,
            "user_id": 999,
            "reference": "SALE-AUTHOR",
        },
        headers=EMPLOYEE_HEADERS,
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == 2


def test_set_transaction_can_zero_stock_and_is_idempotent():
    product_id = create_product_db(quantity=20)
    payload = {
        "product_id": product_id,
        "transaction_type": "SET",
        "quantity": 0,
        "user_id": 999,
        "reference": "STOCKTAKE-1",
    }
    headers = {**ADMIN_HEADERS, "Idempotency-Key": "stocktake-1"}
    first = client.post("/transactions/", json=payload, headers=headers)
    replay = client.post("/transactions/", json=payload, headers=headers)
    assert first.status_code == replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
    assert first.json()["quantity"] == 0
    assert first.json()["user_id"] == 1
    assert client.get(
        f"/products/{product_id}", headers=ADMIN_HEADERS
    ).json()["quantity"] == 0
    assert len(client.get("/transactions/", headers=ADMIN_HEADERS).json()) == 1


def test_employee_cannot_set_stock():
    product_id = create_product_db(quantity=5)
    response = client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "SET",
            "quantity": 0,
            "user_id": 2,
            "reference": "STOCKTAKE",
        },
        headers=EMPLOYEE_HEADERS,
    )
    assert response.status_code == 403
    assert client.get(
        f"/products/{product_id}", headers=ADMIN_HEADERS
    ).json()["quantity"] == 5


# TC-Transaction-01.3
def test_sale_larger_than_stock_no_row_stock_unchanged():
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


# TC-Transaction-01.4
def test_filtering_by_product_and_newest_first():
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


# TC-Transaction-01.5
def test_without_login_401():
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


# TC-Transaction-01.6
def test_post_not_allowed_for_employee_restock():
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
