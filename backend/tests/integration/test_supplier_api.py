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


# TC-Supplier-01.1
def test_create_supplier_201_admin():
    response = client.post(
        "/suppliers/",
        json={
            "name": "ACME Corp",
            "email": "acme@example.com",
            "phone": "1234567890",
            "address": "123 Street",
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "ACME Corp"
    assert data["email"] == "acme@example.com"
    assert "id" in data


# TC-Supplier-01.2
def test_create_supplier_422_invalid_body():
    response = client.post(
        "/suppliers/",
        json={
            "name": "",
            "email": "not-an-email",
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422


# TC-Supplier-01.3
def test_create_supplier_409_duplicate_name():
    client.post(
        "/suppliers/",
        json={"name": "ACME Corp", "email": "acme@example.com"},
        headers=ADMIN_HEADERS,
    )

    response = client.post(
        "/suppliers/",
        json={"name": "acme corp", "email": "other@example.com"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409


# TC-Supplier-01.4
def test_update_supplier_200_admin():
    supplier_id = create_supplier_http()

    response = client.put(
        f"/suppliers/{supplier_id}",
        json={"name": "New Name", "email": "new@example.com"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == supplier_id
    assert data["name"] == "New Name"


# TC-Supplier-01.5
def test_update_supplier_404_missing():
    response = client.put(
        "/suppliers/9999",
        json={"name": "New Name"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404


# TC-Supplier-01.6
def test_employee_create_update_403():
    create_response = client.post(
        "/suppliers/",
        json={"name": "ACME Corp", "email": "acme@example.com"},
        headers=EMPLOYEE_HEADERS,
    )
    assert create_response.status_code == 403

    supplier_id = create_supplier_http()

    update_response = client.put(
        f"/suppliers/{supplier_id}",
        json={"name": "New Name"},
        headers=EMPLOYEE_HEADERS,
    )
    assert update_response.status_code == 403


# TC-Supplier-01.7
def test_create_update_without_login_401():
    response = client.post(
        "/suppliers/",
        json={"name": "ACME Corp", "email": "acme@example.com"},
    )
    assert response.status_code == 401

    response = client.put(
        "/suppliers/1",
        json={"name": "New Name"},
    )
    assert response.status_code == 401


# TC-Supplier-02.1
def test_employee_view_suppliers_200():
    create_supplier_http()

    response = client.get("/suppliers/", headers=EMPLOYEE_HEADERS)

    assert response.status_code == 200
    assert len(response.json()) == 1


# TC-Supplier-02.2
def test_employee_view_supplier_details_200():
    supplier_id = create_supplier_http()

    response = client.get(f"/suppliers/{supplier_id}", headers=EMPLOYEE_HEADERS)

    assert response.status_code == 200
    assert response.json()["id"] == supplier_id


# TC-Supplier-02.3
def test_link_product_201_admin():
    product_id = create_product_db()
    supplier_id = create_supplier_http()

    response = client.post(
        f"/suppliers/{supplier_id}/products/{product_id}",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201


# TC-Supplier-02.4
def test_link_product_409_duplicate():
    product_id = create_product_db()
    supplier_id = create_supplier_http()

    client.post(
        f"/suppliers/{supplier_id}/products/{product_id}",
        headers=ADMIN_HEADERS,
    )

    response = client.post(
        f"/suppliers/{supplier_id}/products/{product_id}",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409


# TC-Supplier-02.5
def test_link_product_404_unknown():
    supplier_id = create_supplier_http()

    response = client.post(
        f"/suppliers/{supplier_id}/products/9999",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404

    product_id = create_product_db()

    response = client.post(
        f"/suppliers/9999/products/{product_id}",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404
