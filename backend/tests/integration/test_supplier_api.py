from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.main import app
from app.models.product import Product
from app.models.supplier import Supplier
from app.routers.suppliers import get_db

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
    setup_database()

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

    teardown_database()


# TC-Supplier-01.2
def test_create_supplier_422_invalid_body():
    setup_database()

    response = client.post(
        "/suppliers/",
        json={
            "name": "",
            "email": "not-an-email",
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422

    teardown_database()


# TC-Supplier-01.3
def test_create_supplier_409_duplicate_name():
    setup_database()

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

    teardown_database()


# TC-Supplier-01.4
def test_update_supplier_200_admin():
    setup_database()

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

    teardown_database()


# TC-Supplier-01.5
def test_update_supplier_404_missing():
    setup_database()

    response = client.put(
        "/suppliers/9999",
        json={"name": "New Name"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404

    teardown_database()


# TC-Supplier-01.6
def test_employee_create_update_403():
    setup_database()

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

    teardown_database()


# TC-Supplier-01.7
def test_create_update_without_login_401():
    setup_database()

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

    teardown_database()


# TC-Supplier-02.1
def test_employee_view_suppliers_200():
    setup_database()

    create_supplier_http()

    response = client.get("/suppliers/", headers=EMPLOYEE_HEADERS)

    assert response.status_code == 200
    assert len(response.json()) == 1

    teardown_database()


# TC-Supplier-02.2
def test_employee_view_supplier_details_200():
    setup_database()

    supplier_id = create_supplier_http()

    response = client.get(f"/suppliers/{supplier_id}", headers=EMPLOYEE_HEADERS)

    assert response.status_code == 200
    assert response.json()["id"] == supplier_id

    teardown_database()


# TC-Supplier-02.3
def test_link_product_201_admin():
    setup_database()

    product_id = create_product_db()
    supplier_id = create_supplier_http()

    response = client.post(
        f"/suppliers/{supplier_id}/products/{product_id}",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201

    teardown_database()


# TC-Supplier-02.4
def test_link_product_409_duplicate():
    setup_database()

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

    teardown_database()


# TC-Supplier-02.5
def test_link_product_404_unknown():
    setup_database()

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

    teardown_database()
