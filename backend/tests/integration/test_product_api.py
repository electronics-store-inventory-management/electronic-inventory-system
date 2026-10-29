from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.core.auth import ADMIN_HEADERS, EMPLOYEE_HEADERS
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

    response = client.post(
        "/products/",
        json={
            "name": "Integration Laptop",
            "category": "Laptop",
            "price": 65000.00,
            "quantity": 20,
            "min_stock_level": 5,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Integration Laptop"
    assert data["category"] == "Laptop"
    assert Decimal(str(data["price"])) == Decimal("65000.00")
    assert data["quantity"] == 20
    assert data["min_stock_level"] == 5
    assert "id" in data

    teardown_database()


def test_view_product():
    setup_database()

    create_response = client.post(
        "/products/",
        json={
            "name": "Integration Phone",
            "category": "Smartphone",
            "price": 30000.00,
            "quantity": 15,
        },
    )

    product_id = create_response.json()["id"]

    response = client.get(
        f"/products/{product_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert data["name"] == "Integration Phone"
    assert data["category"] == "Smartphone"

    teardown_database()


def test_search_products_by_name():
    setup_database()

    client.post(
        "/products/",
        json={
            "name": "Integration Headphones",
            "category": "Headphones",
            "price": 12000.00,
            "quantity": 10,
        },
    )

    response = client.get(
        "/products/?name=Integration"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Integration Headphones"

    teardown_database()


def test_search_products_by_category():
    setup_database()

    client.post(
        "/products/",
        json={
            "name": "Integration Monitor",
            "category": "Monitor",
            "price": 25000.00,
            "quantity": 8,
        },
    )

    response = client.get(
        "/products/?category=Monitor"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["category"] == "Monitor"

    teardown_database()


def test_search_products_by_id():
    setup_database()

    create_response = client.post(
        "/products/",
        json={
            "name": "Integration Keyboard",
            "category": "Accessories",
            "price": 5000.00,
            "quantity": 25,
        },
    )

    product_id = create_response.json()["id"]

    response = client.get(
        f"/products/?product_id={product_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == product_id

    teardown_database()


def test_update_product():
    setup_database()

    create_response = client.post(
        "/products/",
        json={
            "name": "Integration Tablet",
            "category": "Tablet",
            "price": 40000.00,
            "quantity": 10,
        },
    )

    product_id = create_response.json()["id"]

    response = client.put(
        f"/products/{product_id}",
        json={
            "price": 35000.00,
            "quantity": 15,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert Decimal(str(data["price"])) == Decimal("35000.00")
    assert data["quantity"] == 15

    teardown_database()


def test_delete_product():
    setup_database()

    create_response = client.post(
        "/products/",
        json={
            "name": "Integration Mouse",
            "category": "Accessories",
            "price": 2000.00,
            "quantity": 30,
        },
    )

    product_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/products/{product_id}"
    )

    assert delete_response.status_code == 200

    deleted_data = delete_response.json()

    assert deleted_data["id"] == product_id

    get_response = client.get(
        f"/products/{product_id}"
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Product not found"

    teardown_database()


def test_view_nonexistent_product():
    setup_database()

    response = client.get(
        "/products/9999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"

    teardown_database()


def test_low_stock_endpoint_returns_only_below_minimum_products():
    """Verify filtering uses strict less-than and returns the documented fields."""
    setup_database()
    for name, quantity, minimum in [
        ("Below", 2, 5),
        ("Above", 6, 5),
        ("At minimum", 5, 5),
    ]:
        client.post(
            "/products/",
            json={
                "name": name,
                "category": "Accessories",
                "price": 100.00,
                "quantity": quantity,
                "min_stock_level": minimum,
            },
        )

    response = client.get("/products/low-stock", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Below", "quantity": 2, "min_stock_level": 5}
    ]
    teardown_database()


def test_low_stock_endpoint_returns_empty_for_empty_inventory():
    """An empty database should produce a successful empty low-stock response."""
    setup_database()

    response = client.get("/products/low-stock", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == []
    teardown_database()


def test_low_stock_endpoint_requires_admin_access():
    """Match the admin-only access rule used by the inventory report endpoint."""
    setup_database()

    assert client.get("/products/low-stock").status_code == 401
    assert client.get(
        "/products/low-stock", headers=EMPLOYEE_HEADERS
    ).status_code == 403
    teardown_database()


def test_product_api_rejects_negative_quantity_and_threshold():
    """Invalid negative stock values must be rejected by request validation."""
    setup_database()
    base = {
        "name": "Invalid Product",
        "category": "Accessories",
        "price": 100.00,
        "quantity": 2,
        "min_stock_level": 5,
    }

    for field in ("quantity", "min_stock_level"):
        response = client.post("/products/", json={**base, field: -1})
        assert response.status_code == 422

    teardown_database()


def test_product_api_updates_minimum_stock_level_and_rejects_negative_value():
    """Thresholds can be edited independently, while negative edits return 422."""
    setup_database()
    create_response = client.post(
        "/products/",
        json={
            "name": "Threshold Product",
            "category": "Accessories",
            "price": 100.00,
            "quantity": 8,
            "min_stock_level": 2,
        },
    )
    product_id = create_response.json()["id"]

    update_response = client.put(
        f"/products/{product_id}",
        json={"min_stock_level": 5},
    )
    assert update_response.status_code == 200
    assert update_response.json()["min_stock_level"] == 5

    invalid_response = client.put(
        f"/products/{product_id}",
        json={"min_stock_level": -1},
    )
    assert invalid_response.status_code == 422
    teardown_database()
