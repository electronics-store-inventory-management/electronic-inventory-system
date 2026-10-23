from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.report import InventoryReport, LowStockProduct


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

    low_stock = [
        item
        for item in product_responses
        if item.min_stock_level > 0 and item.quantity < item.min_stock_level
    ]

    return InventoryReport(products=product_responses, low_stock=low_stock)
