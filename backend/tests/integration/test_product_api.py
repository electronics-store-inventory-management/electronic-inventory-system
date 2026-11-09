from decimal import Decimal
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.auth_helpers import ADMIN_HEADERS, EMPLOYEE_HEADERS
from tests.test_users import seed_test_users

from app.database.database import Base, get_db as shared_get_db, settings
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
app.dependency_overrides[shared_get_db] = override_get_db

client = TestClient(app)


def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_test_users(db)
    finally:
        db.close()


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
                "min_stock_level": 5,
            },
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Integration Laptop"
        assert data["category"] == "Laptop"
        assert Decimal(str(data["price"])) == Decimal("65000.00")
        assert data["quantity"] == 20
        assert data["min_stock_level"] == 5
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
        response = client.get("/products/")
        assert response.status_code == 401

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

        response = client.put(
            f"/products/{product_id}",
            json={"quantity": 10},
            headers=EMPLOYEE_HEADERS,
        )
        assert response.status_code == 403

        response = client.delete(
            f"/products/{product_id}",
            headers=EMPLOYEE_HEADERS,
        )
        assert response.status_code == 403
    finally:
        teardown_database()


def test_product_search_response_within_three_seconds():
    setup_database()
    try:
        db = TestingSessionLocal()
        try:
            from app.models.product import Product

            products = [
                Product(
                    name=f"Performance Laptop {i}",
                    category="Laptops",
                    price=Decimal("50000.00"),
                    quantity=10,
                )
                for i in range(1000)
            ]

            db.add_all(products)
            db.commit()
        finally:
            db.close()

        start_time = time.perf_counter()

        response = client.get(
            "/products/?name=Performance",
            headers=EMPLOYEE_HEADERS,
        )

        elapsed_time = time.perf_counter() - start_time

        assert response.status_code == 200
        assert len(response.json()) == 1000
        assert elapsed_time < 3.0, (
            f"Product search took {elapsed_time:.3f} seconds; "
            "the requirement is under 3 seconds."
        )
    finally:
        teardown_database()


def test_register_user_hashes_password_and_login_returns_token():
    from app.core.password_security import verify_password
    from app.models.user import User

    setup_database()
    try:
        username = "auth_test_employee"
        password = "SecureTestPassword123!"

        register_response = client.post(
            "/auth/register",
            json={"username": username, "password": password},
        )

        assert register_response.status_code == 201
        assert register_response.json()["username"] == username
        assert register_response.json()["role"] == "employee"

        db = TestingSessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            assert user is not None
            assert user.hashed_password != password
            assert verify_password(password, user.hashed_password)
        finally:
            db.close()

        login_response = client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )

        assert login_response.status_code == 200
        assert login_response.json()["token_type"] == "bearer"
        assert login_response.json()["access_token"]
    finally:
        teardown_database()


def test_register_rejects_duplicate_username():
    setup_database()
    try:
        payload = {
            "username": "duplicate_test_user",
            "password": "SecureTestPassword123!",
        }

        first_response = client.post("/auth/register", json=payload)
        second_response = client.post("/auth/register", json=payload)

        assert first_response.status_code == 201
        assert second_response.status_code == 409
    finally:
        teardown_database()


def test_login_rejects_invalid_credentials():
    setup_database()
    try:
        response = client.post(
            "/auth/login",
            json={
                "username": "nonexistent_test_user",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
    finally:
        teardown_database()


def test_product_routes_reject_invalid_token():
    setup_database()
    try:
        response = client.get(
            "/products/",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
    finally:
        teardown_database()


def test_product_routes_reject_expired_token():
    setup_database()
    try:
        now = datetime.now(timezone.utc)

        expired_token = jwt.encode(
            {
                "sub": "2",
                "username": "employee",
                "iat": now - timedelta(hours=2),
                "exp": now - timedelta(hours=1),
            },
            settings.JWT_SECRET_KEY,
            algorithm="HS256",
        )

        response = client.get(
            "/products/",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
    finally:
        teardown_database()


def test_low_stock_endpoint_returns_only_below_minimum_products():
    """Verify filtering uses strict less-than and returns documented fields."""
    setup_database()
    try:
        for name, quantity, minimum in [
            ("Below", 2, 5),
            ("Above", 6, 5),
            ("At minimum", 5, 5),
        ]:
            response = client.post(
                "/products/",
                json={
                    "name": name,
                    "category": "Accessories",
                    "price": 100.00,
                    "quantity": quantity,
                    "min_stock_level": minimum,
                },
                headers=ADMIN_HEADERS,
            )
            assert response.status_code == 201

        response = client.get(
            "/products/low-stock",
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == 200
        assert response.json() == [
            {"id": 1, "name": "Below", "quantity": 2, "min_stock_level": 5}
        ]
    finally:
        teardown_database()


def test_low_stock_endpoint_returns_empty_for_empty_inventory():
    """An empty database should produce a successful empty low-stock response."""
    setup_database()
    try:
        response = client.get(
            "/products/low-stock",
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == 200
        assert response.json() == []
    finally:
        teardown_database()


def test_low_stock_endpoint_requires_admin_access():
    """Verify that the low-stock endpoint is admin-only."""
    setup_database()
    try:
        assert client.get("/products/low-stock").status_code == 401

        response = client.get(
            "/products/low-stock",
            headers=EMPLOYEE_HEADERS,
        )
        assert response.status_code == 403
    finally:
        teardown_database()


def test_product_api_rejects_negative_quantity_and_threshold():
    """Invalid negative stock values must be rejected by request validation."""
    setup_database()
    try:
        base = {
            "name": "Invalid Product",
            "category": "Accessories",
            "price": 100.00,
            "quantity": 2,
            "min_stock_level": 5,
        }

        for field in ("quantity", "min_stock_level"):
            response = client.post(
                "/products/",
                json={**base, field: -1},
                headers=ADMIN_HEADERS,
            )
            assert response.status_code == 422
    finally:
        teardown_database()


def test_product_api_updates_minimum_stock_level_and_rejects_negative_value():
    """Thresholds can be edited independently, while negative edits return 422."""
    setup_database()
    try:
        create_response = client.post(
            "/products/",
            json={
                "name": "Threshold Product",
                "category": "Accessories",
                "price": 100.00,
                "quantity": 8,
                "min_stock_level": 2,
            },
            headers=ADMIN_HEADERS,
        )

        assert create_response.status_code == 201
        product_id = create_response.json()["id"]

        update_response = client.put(
            f"/products/{product_id}",
            json={"min_stock_level": 5},
            headers=ADMIN_HEADERS,
        )

        assert update_response.status_code == 200
        assert update_response.json()["min_stock_level"] == 5

        invalid_response = client.put(
            f"/products/{product_id}",
            json={"min_stock_level": -1},
            headers=ADMIN_HEADERS,
        )

        assert invalid_response.status_code == 422
    finally:
        teardown_database()