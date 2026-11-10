"""Create legacy application tables for fresh databases.

On an existing database, leave all existing tables and rows untouched. This
revision acts as a baseline so the following revision can apply the inventory
integrity changes to either a fresh database or the pre-Alembic schema.
"""
from alembic import op
import sqlalchemy as sa


revision = "20261108_00"
down_revision = None
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    tables = _tables()

    if "products" not in tables:
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=False),
            sa.Column("price", sa.Numeric(10, 2), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("min_stock_level", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_products_id", "products", ["id"], unique=False)

    if "suppliers" not in tables:
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=200), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("address", sa.String(length=200), nullable=True),
        )
        op.create_index("ix_suppliers_id", "suppliers", ["id"], unique=False)
        op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=False)
        op.create_index("ix_suppliers_email", "suppliers", ["email"], unique=False)

    if "product_suppliers" not in tables:
        op.create_table(
            "product_suppliers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id"),
                nullable=False,
            ),
            sa.Column(
                "supplier_id",
                sa.Integer(),
                sa.ForeignKey("suppliers.id"),
                nullable=False,
            ),
        )
        op.create_index("ix_product_suppliers_id", "product_suppliers", ["id"], unique=False)
        op.create_index(
            "ix_product_suppliers_product_id", "product_suppliers", ["product_id"], unique=False
        )
        op.create_index(
            "ix_product_suppliers_supplier_id", "product_suppliers", ["supplier_id"], unique=False
        )

    if "inventory_transactions" not in tables:
        op.create_table(
            "inventory_transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("transaction_type", sa.String(length=20), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("reference", sa.String(length=200), nullable=False),
        )
        op.create_index("ix_inventory_transactions_id", "inventory_transactions", ["id"], unique=False)
        op.create_index(
            "ix_inventory_transactions_product_id",
            "inventory_transactions",
            ["product_id"],
            unique=False,
        )

    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("entity", sa.String(length=100), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_audit_logs_id", "audit_logs", ["id"], unique=False)


def downgrade():
    # This is a baseline for both fresh and pre-existing installations. It
    # cannot safely determine which tables are safe to delete on downgrade.
    pass
