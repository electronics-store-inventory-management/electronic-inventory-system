
from app.core.password_security import hash_password
from app.database.database import Base, SessionLocal, engine
from app.models.product import Product
from app.models.supplier import ProductSupplier, Supplier
from app.models.transaction import InventoryTransaction
from app.models.user import User
from app.services.transaction_service import record_transaction
from app.schemas.transaction import InventoryTransactionCreate

# Ensure all tables exist
Base.metadata.create_all(engine)

db = SessionLocal()


def ensure_user(user_id, username, role, password):
    existing = db.query(User).filter(User.id == user_id).first()
    if existing is None:
        db.add(
            User(
                id=user_id,
                username=username,
                role=role,
                hashed_password=hash_password(password),
            )
        )
        db.flush()
    return existing or db.query(User).filter(User.id == user_id).first()


def ensure_product(product_id, name, category, price, quantity, min_stock_level=0):
    existing = db.query(Product).filter(Product.id == product_id).first()
    if existing is None:
        db.add(
            Product(
                id=product_id,
                name=name,
                category=category,
                price=price,
                quantity=quantity,
                min_stock_level=min_stock_level,
            )
        )
        db.flush()
    return existing or db.query(Product).filter(Product.id == product_id).first()


def ensure_supplier(supplier_id, name, email=None, phone=None, address=None):
    existing = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if existing is None:
        db.add(
            Supplier(
                id=supplier_id,
                name=name,
                email=email,
                phone=phone,
                address=address,
            )
        )
        db.flush()
    return existing or db.query(Supplier).filter(Supplier.id == supplier_id).first()


try:
    admin = ensure_user(1, "admin", "admin", "AdminPass123!")
    employee = ensure_user(2, "employee", "employee", "EmployeePass123!")

    products = [
        ensure_product(1, "Wireless Headphones", "Audio", 1499.00, 25, 5),
        ensure_product(2, "USB-C Charging Cable", "Accessories", 299.00, 100, 20),
        ensure_product(3, "Bluetooth Mouse", "Accessories", 799.00, 12, 3),
        ensure_product(4, "4K Webcam", "Peripherals", 4599.00, 8, 2),
        ensure_product(5, "Mechanical Keyboard", "Peripherals", 3299.00, 15, 4),
    ]

    suppliers = [
        ensure_supplier(
            1,
            "TechDistributors Inc",
            email="sales@techdist.com",
            phone="+1-555-0101",
            address="123 Industrial Ave, Tech City",
        ),
        ensure_supplier(
            2,
            "Global Electronics Supply",
            email="orders@globalelec.com",
            phone="+1-555-0202",
            address="456 Component Blvd, Parts Town",
        ),
        ensure_supplier(
            3,
            "Premium Audio Wholesale",
            email="contact@premiumaudio.net",
            phone="+1-555-0303",
            address="789 Soundwave Dr, Audio Valley",
        ),
        ensure_supplier(
            4,
            "Peripherals Direct",
            email="info@peripheralsdirect.biz",
            phone="+1-555-0404",
            address="321 Peripheral Way, Device District",
        ),
    ]

    product_supplier_links = [
        (1, 1), (1, 3), (2, 2), (2, 4), (3, 3), (3, 2), (4, 4), (4, 1), (5, 4), (5, 2),
    ]

    db.commit()

    for product_id, supplier_id in product_supplier_links:
        existing = (
            db.query(ProductSupplier)
            .filter(
                ProductSupplier.product_id == product_id,
                ProductSupplier.supplier_id == supplier_id,
            )
            .first()
        )
        if existing is None:
            db.add(ProductSupplier(product_id=product_id, supplier_id=supplier_id))

    transactions = [
        InventoryTransactionCreate(product_id=1, transaction_type="ADD", quantity=30, user_id=admin.id, reference="INIT-STOCK-2024-001"),
        InventoryTransactionCreate(product_id=2, transaction_type="ADD", quantity=100, user_id=admin.id, reference="INIT-STOCK-2024-002"),
        InventoryTransactionCreate(product_id=3, transaction_type="ADD", quantity=20, user_id=admin.id, reference="INIT-STOCK-2024-003"),
        InventoryTransactionCreate(product_id=4, transaction_type="ADD", quantity=10, user_id=admin.id, reference="INIT-STOCK-2024-004"),
        InventoryTransactionCreate(product_id=5, transaction_type="ADD", quantity=20, user_id=admin.id, reference="INIT-STOCK-2024-005"),
        InventoryTransactionCreate(product_id=1, transaction_type="DEDUCT", quantity=5, user_id=employee.id, reference="SALE-ORD-1001"),
        InventoryTransactionCreate(product_id=2, transaction_type="DEDUCT", quantity=15, user_id=employee.id, reference="SALE-ORD-1002"),
        InventoryTransactionCreate(product_id=4, transaction_type="DEDUCT", quantity=2, user_id=employee.id, reference="SALE-ORD-1003"),
        InventoryTransactionCreate(product_id=3, transaction_type="SET", quantity=10, user_id=admin.id, reference="AUDIT-ADJ-2024-001"),
    ]

    for tx in transactions:
        record_transaction(db, tx, authenticated_user_id=admin.id)

    db.commit()
    print("Seed data created successfully.")
    print("Users: admin/AdminPass123! (admin), employee/EmployeePass123! (employee)")
finally:
    db.close()
