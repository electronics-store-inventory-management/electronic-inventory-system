from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.report import InventoryReport, LowStockProduct


def get_low_stock_products(db: Session) -> list[Product]:
    """Return products whose available quantity is below their configured threshold."""
    # Comparing the columns in SQL lets the database filter inventory efficiently.
    # A zero threshold cannot match because product quantities are validated as non-negative.
    return (
        db.query(Product)
        # Keep the existing report rule: a zero threshold means "not monitored".
        .filter(Product.min_stock_level > 0)
        .filter(Product.quantity < Product.min_stock_level)
        .order_by(Product.name)
        .all()
    )


def generate_report(db: Session) -> InventoryReport:
    products = db.query(Product).order_by(Product.name).all()

    product_responses = [
        LowStockProduct(
            id=product.id,
            name=product.name,
            quantity=product.quantity,
            min_stock_level=product.min_stock_level,
        )
        for product in products
    ]

    # Use the shared detection query so reports and the dedicated endpoint agree.
    low_stock = [
        LowStockProduct(
            id=product.id,
            name=product.name,
            quantity=product.quantity,
            min_stock_level=product.min_stock_level,
        )
        for product in get_low_stock_products(db)
    ]

    return InventoryReport(products=product_responses, low_stock=low_stock)
