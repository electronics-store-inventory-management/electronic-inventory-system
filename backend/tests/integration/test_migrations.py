from pathlib import Path
from datetime import datetime

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
    inspect,
    insert,
    select,
    text,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]


def upgrade_database(engine, revision="head"):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)


def test_migrations_initialize_fresh_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.sqlite'}")

    upgrade_database(engine)

    inspector = inspect(engine)
    assert {
        "products",
        "inventory_transactions",
        "audit_logs",
        "suppliers",
        "product_suppliers",
        "alembic_version",
        "users",
    }.issubset(set(inspector.get_table_names()))
    assert any(index["unique"] and index["column_names"] == ["username"] for index in inspector.get_indexes("users"))
    assert "idempotency_key" in {
        column["name"] for column in inspector.get_columns("inventory_transactions")
    }
    assert {item["name"] for item in inspector.get_check_constraints("products")} == {
        "ck_products_quantity_nonnegative",
        "ck_products_min_stock_nonnegative",
    }
    assert {item["name"] for item in inspector.get_check_constraints("inventory_transactions")} == {
        "ck_inventory_transaction_type",
        "ck_inventory_transaction_quantity",
    }


def test_migrations_preserve_existing_database_rows(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'existing.sqlite'}")
    metadata = MetaData()
    products = Table(
        "products",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100), nullable=False),
        Column("category", String(100), nullable=False),
        Column("price", Numeric(10, 2), nullable=False),
        Column("quantity", Integer, nullable=False),
        Column("min_stock_level", Integer, nullable=False),
    )
    transactions = Table(
        "inventory_transactions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("product_id", Integer, nullable=False),
        Column("transaction_type", String(20), nullable=False),
        Column("quantity", Integer, nullable=False),
        Column("date", DateTime(timezone=True), nullable=False),
        Column("user_id", Integer, nullable=False),
        Column("reference", String(200), nullable=False),
    )
    suppliers = Table(
        "suppliers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100), nullable=False),
        Column("email", String(200)),
        Column("phone", String(50)),
        Column("address", String(200)),
    )
    product_suppliers = Table(
        "product_suppliers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("product_id", Integer, nullable=False),
        Column("supplier_id", Integer, nullable=False),
    )
    audit_logs = Table(
        "audit_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, nullable=False),
        Column("action", String(100), nullable=False),
        Column("entity", String(100), nullable=False),
        Column("entity_id", Integer, nullable=False),
        Column("timestamp", DateTime(timezone=True), nullable=False),
    )
    users = Table(
        "users", metadata,
        Column("id", Integer, primary_key=True),
        Column("username", String(50), nullable=False, unique=True),
        Column("hashed_password", String(255), nullable=False),
        Column("role", String(20), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(insert(users).values(id=8, username="existing_admin", hashed_password="fixture-hash", role="admin"))
        connection.execute(
            insert(products).values(
                id=41,
                name="Existing Product",
                category="Audio",
                price=125.50,
                quantity=7,
                min_stock_level=2,
            )
        )
        connection.execute(
            insert(transactions).values(
                id=72,
                product_id=41,
                transaction_type="ADD",
                quantity=3,
                date=datetime(2026, 1, 1),
                user_id=1,
                reference="OLD-RESTOCK",
            )
        )
        connection.execute(
            insert(suppliers).values(
                id=15,
                name="Existing Supplier",
                email="supplier@example.test",
                phone="555-0100",
                address="Existing address",
            )
        )
        connection.execute(
            insert(product_suppliers).values(id=22, product_id=41, supplier_id=15)
        )
        connection.execute(
            insert(audit_logs).values(
                id=31,
                user_id=1,
                action="inventory_add",
                entity="inventory_transaction",
                entity_id=72,
                timestamp=datetime(2026, 1, 1),
            )
        )

    upgrade_database(engine)

    migrated_metadata = MetaData()
    migrated_transactions = Table(
        "inventory_transactions", migrated_metadata, autoload_with=engine
    )
    with engine.connect() as connection:
        assert connection.execute(select(users)).one() == (8, "existing_admin", "fixture-hash", "admin")
        product = connection.execute(select(products)).one()
        transaction = connection.execute(
            select(migrated_transactions).where(migrated_transactions.c.id == 72)
        ).one()
        supplier = connection.execute(select(suppliers)).one()
        link = connection.execute(select(product_suppliers)).one()
        audit = connection.execute(select(audit_logs)).one()
        assert (product.id, product.name, product.quantity) == (41, "Existing Product", 7)
        assert (transaction.id, transaction.product_id, transaction.reference) == (
            72,
            41,
            "OLD-RESTOCK",
        )
        assert transaction.idempotency_key is None
        assert (supplier.id, supplier.name) == (15, "Existing Supplier")
        assert (link.id, link.product_id, link.supplier_id) == (22, 41, 15)
        assert (audit.id, audit.action, audit.entity_id) == (31, "inventory_add", 72)
    assert "idempotency_key" in {
        column["name"] for column in inspect(engine).get_columns("inventory_transactions")
    }


@pytest.mark.parametrize(("schema", "extra", "reason"), [
    ("id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL, hashed_password VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL",
     "", "username requires"),
    ("id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL, hashed_password VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL",
     "CREATE UNIQUE INDEX partial_username ON users(username) WHERE role = 'employee'", "username requires"),
    ("id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE, hashed_password VARCHAR(255) NOT NULL",
     "", "role must"),
    ("id INTEGER NOT NULL, username VARCHAR(50) NOT NULL UNIQUE, hashed_password VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL",
     "", "id must be the sole primary key"),
])
def test_migration_rejects_legacy_schema_and_preserves_rows(tmp_path, schema, extra, reason):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite'}")
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE users ({schema})"))
        columns = [column["name"] for column in inspect(connection).get_columns("users")]
        values = {"id": 7, "username": "legacy_admin", "hashed_password": "fixture-hash", "role": "admin"}
        connection.execute(text(
            f"INSERT INTO users ({', '.join(columns)}) VALUES ({', '.join(':' + name for name in columns)})"
        ), values)
        if extra:
            connection.execute(text(extra))
    upgrade_database(engine, "20261108_01")
    with pytest.raises(RuntimeError, match=reason):
        upgrade_database(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT * FROM users")).one() == tuple(values[name] for name in columns)
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20261108_01"
    engine.dispose()
