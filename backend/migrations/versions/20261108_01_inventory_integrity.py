"""Add inventory transaction integrity constraints and idempotency."""
from alembic import op
import sqlalchemy as sa

revision = "20261108_01"
down_revision = "20261108_00"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("inventory_transactions") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(length=200), nullable=True))
        batch.create_check_constraint(
            "ck_inventory_transaction_type",
            "transaction_type IN ('ADD', 'DEDUCT', 'SET')",
        )
        batch.create_check_constraint(
            "ck_inventory_transaction_quantity",
            "(transaction_type = 'SET' AND quantity >= 0) OR "
            "(transaction_type IN ('ADD', 'DEDUCT') AND quantity > 0)",
        )
        batch.create_foreign_key(
            "fk_inventory_transactions_product_id_products",
            "products",
            ["product_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_inventory_transactions_idempotency_key",
        "inventory_transactions",
        ["idempotency_key"],
        unique=True,
    )
    with op.batch_alter_table("products") as batch:
        batch.create_check_constraint("ck_products_quantity_nonnegative", "quantity >= 0")
        batch.create_check_constraint(
            "ck_products_min_stock_nonnegative", "min_stock_level >= 0"
        )


def downgrade():
    op.drop_index("ix_inventory_transactions_idempotency_key", table_name="inventory_transactions")
    with op.batch_alter_table("inventory_transactions") as batch:
        batch.drop_constraint("fk_inventory_transactions_product_id_products", type_="foreignkey")
        batch.drop_constraint("ck_inventory_transaction_quantity", type_="check")
        batch.drop_constraint("ck_inventory_transaction_type", type_="check")
        batch.drop_column("idempotency_key")
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("ck_products_min_stock_nonnegative", type_="check")
        batch.drop_constraint("ck_products_quantity_nonnegative", type_="check")
