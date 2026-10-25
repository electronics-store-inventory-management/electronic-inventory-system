from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.database.database import Base, get_db as db_get_db
from app.main import app
from app.models.product import Product
from app.models.supplier import Supplier
from app.routers.audit_logs import get_db as audit_get_db
from app.routers.product import get_db as product_get_db
from app.routers.reports import get_db as reports_get_db
from app.routers.suppliers import get_db as suppliers_get_db
from app.routers.transactions import get_db as transactions_get_db

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


def create_supplier_http(name="ACME Corp", email="acme@example.com"):
    response = client.post(
        "/suppliers/",
        json={"name": name, "email": email},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()["id"]


# TC-Audit-01.1 / TC-Sec-05.1
def test_adding_supplier_is_audited():
    before = len(client.get("/audit-logs/", headers=ADMIN_HEADERS).json())

    create_supplier_http()

    after = len(client.get("/audit-logs/", headers=ADMIN_HEADERS).json())

    assert after == before + 1

    latest = client.get("/audit-logs/", headers=ADMIN_HEADERS).json()[0]
    assert latest["user_id"] == 1
    assert latest["action"] == "create_supplier"
    assert latest["entity"] == "supplier"
    assert latest["entity_id"] is not None
    assert latest["timestamp"] is not None


# TC-Sec-05.2
def test_employee_sale_audited_with_employee_id():
    product_id = create_product_db(quantity=100)

    client.post(
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

    logs = client.get("/audit-logs/", headers=ADMIN_HEADERS).json()

    sale_logs = [log for log in logs if log["action"] == "inventory_deduct"]

    assert len(sale_logs) >= 1
    assert sale_logs[0]["user_id"] == 2
    assert sale_logs[0]["timestamp"] is not None


# TC-Audit-01.3
def test_filter_by_user_entity_and_action():
    create_supplier_http()
    create_supplier_http(name="Other", email="other@example.com")
    product_id = create_product_db(quantity=100)
    client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "ADD",
            "quantity": 5,
            "user_id": 1,
            "reference": "REF",
        },
        headers=ADMIN_HEADERS,
    )

    by_user = client.get("/audit-logs/?user_id=1", headers=ADMIN_HEADERS).json()
    assert all(log["user_id"] == 1 for log in by_user)

    by_entity = client.get("/audit-logs/?entity=supplier", headers=ADMIN_HEADERS).json()
    assert all(log["entity"] == "supplier" for log in by_entity)

    by_action = client.get("/audit-logs/?action=create_supplier", headers=ADMIN_HEADERS).json()
    assert all(log["action"] == "create_supplier" for log in by_action)


# TC-Sec-05.3
def test_employee_audit_logs_403():
    response = client.get("/audit-logs/", headers=EMPLOYEE_HEADERS)

    assert response.status_code == 403


# TC-Sec-05.4
def test_no_login_audit_logs_401():
    response = client.get("/audit-logs/")

    assert response.status_code == 401


# TC-Sec-05.5
def test_no_routes_to_change_or_delete_audit_records():
    # POST is not allowed on the existing read-only route
    response = client.post("/audit-logs/", json={}, headers=ADMIN_HEADERS)
    assert response.status_code == 405

    # No routes exist to change or delete audit records
    response = client.put("/audit-logs/1", json={}, headers=ADMIN_HEADERS)
    assert response.status_code == 404

    response = client.delete("/audit-logs/1", headers=ADMIN_HEADERS)
    assert response.status_code == 404


# TC-Sec-05.6
def test_every_audited_operation_produces_exactly_one_row():
    before = len(client.get("/audit-logs/", headers=ADMIN_HEADERS).json())

    create_supplier_http()

    client.put(
        "/suppliers/1",
        json={"name": "Updated"},
        headers=ADMIN_HEADERS,
    )

    product_id = create_product_db(quantity=100)
    client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "ADD",
            "quantity": 5,
            "user_id": 1,
            "reference": "REF",
        },
        headers=ADMIN_HEADERS,
    )

    client.post(
        "/transactions/",
        json={
            "product_id": product_id,
            "transaction_type": "DEDUCT",
            "quantity": 2,
            "user_id": 2,
            "reference": "REF",
        },
        headers=EMPLOYEE_HEADERS,
    )

    after = len(client.get("/audit-logs/", headers=ADMIN_HEADERS).json())

    assert after == before + 4

    logs = client.get("/audit-logs/", headers=ADMIN_HEADERS).json()
    for log in logs[before:]:
        assert log["user_id"] is not None
        assert log["timestamp"] is not None
