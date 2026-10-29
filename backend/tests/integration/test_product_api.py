from decimal import Decimal

from app.core.auth import ADMIN_HEADERS, EMPLOYEE_HEADERS
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.main import app
from app.routers.product import get_db


# Use a separate in-memory SQLite database for integration tests.
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


def test_add_product():
    setup_database()
    try:
        response = client.post(
            "/products/",
            json={
                "name": "Integration Laptop",
                "category": "Laptop",
                "price": 65000.00,
                "quantity": 20,
            },
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Integration Laptop"
        assert data["category"] == "Laptop"
        assert Decimal(str(data["price"])) == Decimal("65000.00")
        assert data["quantity"] == 20
        assert "id" in data
    finally:
        teardown_database()


def test_view_product():
    setup_database()
    try:
        create_response = client.post(
            "/products/",
            json={
                "name": "Integration Phone",
                "category": "Smartphone",
                "price": 30000.00,
                "quantity": 15,
            },
            headers=ADMIN_HEADERS,
        )
        assert create_response.status_code == 201
        product_id = create_response.json()["id"]

        response = client.get(
            f"/products/{product_id}",
            headers=EMPLOYEE_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        assert data["name"] == "Integration Phone"
        assert data["category"] == "Smartphone"
    finally:
        teardown_database()


def test_search_products_by_name():
    setup_database()
    try:
        create_response = client.post(
            "/products/",
            json={
                "name": "Integration Headphones",
                "category": "Headphones",
                "price": 12000.00,
                "quantity": 10,
            },
            headers=ADMIN_HEADERS,
        )
        assert create_response.status_code == 201

        response = client.get(
            "/products/?name=Integration",
            headers=EMPLOYEE_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Integration Headphones"
    finally:
        teardown_database()


def test_search_products_by_category():
    setup_database()
    try:
        create_response = client.post(
            "/products/",
            json={
                "name": "Integration Monitor",
                "category": "Monitor",
                "price": 25000.00,
                "quantity": 8,
            },
            headers=ADMIN_HEADERS,
        )
        assert create_response.status_code == 201

        response = client.get(
            "/products/?category=Monitor",
            headers=EMPLOYEE_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "Monitor"
    finally:
        teardown_database()


def test_search_products_by_id():
    setup_database()
    try:
        create_response = client.post(
            "/products/",
            json={
                "name": "Integration Keyboard",
                "category": "Accessories",
                "price": 5000.00,
                "quantity": 25,
            },
            headers=ADMIN_HEADERS,
        )
        assert create_response.status_code == 201
        product_id = create_response.json()["id"]

        response = client.get(
            f"/products/?product_id={product_id}",
            headers=EMPLOYEE_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == product_id
    finally:
        teardown_database()


def test_update_product():
    setup_database()
    try:
        create_response = client.post(
            "/products/",
            json={
                "name": "Integration Tablet",
                "category": "Tablet",
                "price": 40000.00,
                "quantity": 10,
            },
            headers=ADMIN_HEADERS,
        )
        assert create_response.status_code == 201
        product_id = create_response.json()["id"]

        response = client.put(
            f"/products/{product_id}",
            json={
                "price": 35000.00,
                "quantity": 15,
            },
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        assert Decimal(str(data["price"])) == Decimal("35000.00")
        assert data["quantity"] == 15
    finally:
        teardown_database()


def test_delete_product():
    setup_database()
    try:
        create_response = client.post(
            "/products/",
            json={
                "name": "Integration Mouse",
                "category": "Accessories",
                "price": 2000.00,
                "quantity": 30,
            },
            headers=ADMIN_HEADERS,
        )
        assert create_response.status_code == 201
        product_id = create_response.json()["id"]

        delete_response = client.delete(
            f"/products/{product_id}",
            headers=ADMIN_HEADERS,
        )

        assert delete_response.status_code == 200
        assert delete_response.json()["id"] == product_id

        get_response = client.get(
            f"/products/{product_id}",
            headers=EMPLOYEE_HEADERS,
        )

        assert get_response.status_code == 404
        assert get_response.json()["detail"] == "Product not found"
    finally:
        teardown_database()


def test_view_nonexistent_product():
    setup_database()
    try:
        response = client.get(
            "/products/9999",
            headers=EMPLOYEE_HEADERS,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"
    finally:
        teardown_database()


def test_product_routes_require_authentication():
    setup_database()
    try:
        # Listing products without authentication must fail.
        response = client.get("/products/")
        assert response.status_code == 401

        # Adding products without authentication must fail.
        response = client.post(
            "/products/",
            json={
                "name": "Unauthenticated Product",
                "category": "Test",
                "price": 100.00,
                "quantity": 1,
            },
        )
        assert response.status_code == 401
    finally:
        teardown_database()


def test_employee_cannot_manage_products():
    setup_database()
    try:
        # An admin creates a product for the permission tests.
        create_response = client.post(
            "/products/",
            json={
                "name": "Protected Product",
                "category": "Test",
                "price": 100.00,
                "quantity": 5,
            },
            headers=ADMIN_HEADERS,
        )
        assert create_response.status_code == 201
        product_id = create_response.json()["id"]

        # Employees cannot add products.
        response = client.post(
            "/products/",
            json={
                "name": "Employee Product",
                "category": "Test",
                "price": 200.00,
                "quantity": 2,
            },
            headers=EMPLOYEE_HEADERS,
        )
        assert response.status_code == 403

        # Employees cannot update products.
        response = client.put(
            f"/products/{product_id}",
            json={"quantity": 10},
            headers=EMPLOYEE_HEADERS,
        )
        assert response.status_code == 403

        # Employees cannot delete products.
        response = client.delete(
            f"/products/{product_id}",
            headers=EMPLOYEE_HEADERS,
        )
        assert response.status_code == 403
    finally:
        teardown_database()
