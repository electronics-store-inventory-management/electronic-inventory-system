from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database.database import Base


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('ADD', 'DEDUCT', 'SET')",
            name="ck_inventory_transaction_type",
        ),
        CheckConstraint(
            "(transaction_type = 'SET' AND quantity >= 0) OR "
            "(transaction_type IN ('ADD', 'DEDUCT') AND quantity > 0)",
            name="ck_inventory_transaction_quantity",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(Integer, nullable=False)
    reference = Column(String(200), nullable=False)
    idempotency_key = Column(String(200), nullable=True, unique=True, index=True)
