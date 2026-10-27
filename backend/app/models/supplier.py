from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(200), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(200), nullable=True)

    product_suppliers = relationship("ProductSupplier", back_populates="supplier")


class ProductSupplier(Base):
    __tablename__ = "product_suppliers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    supplier = relationship("Supplier", back_populates="product_suppliers")
