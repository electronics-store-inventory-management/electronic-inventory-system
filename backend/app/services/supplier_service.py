from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.models.product import Product
from app.models.supplier import ProductSupplier, Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.audit_service import log_audit


def get_supplier_by_name(db: Session, name: str) -> Supplier | None:
    return db.query(Supplier).filter(Supplier.name.ilike(name)).first()


def create_supplier(
    db: Session,
    supplier_data: SupplierCreate,
    user_id: int,
) -> Supplier:
    existing = get_supplier_by_name(db, supplier_data.name)

    if existing is not None:
        raise ConflictError("Supplier already exists")

    supplier = Supplier(
        name=supplier_data.name,
        email=supplier_data.email,
        phone=supplier_data.phone,
        address=supplier_data.address,
    )

    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    log_audit(
        db,
        user_id=user_id,
        action="create_supplier",
        entity="supplier",
        entity_id=supplier.id,
    )
    db.commit()

    return supplier


def get_supplier(db: Session, supplier_id: int) -> Supplier | None:
    return db.query(Supplier).filter(Supplier.id == supplier_id).first()


def get_suppliers(db: Session) -> list[Supplier]:
    return db.query(Supplier).order_by(Supplier.name).all()


def update_supplier(
    db: Session,
    supplier_id: int,
    supplier_data: SupplierUpdate,
    user_id: int,
) -> Supplier | None:
    supplier = get_supplier(db, supplier_id)

    if supplier is None:
        return None

    update_data = supplier_data.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        new_name = update_data["name"]
        existing = get_supplier_by_name(db, new_name)
        if existing is not None and existing.id != supplier_id:
            raise ConflictError("Supplier already exists")
        supplier.name = new_name

    if "email" in update_data and update_data["email"] is not None:
        supplier.email = update_data["email"]

    if "phone" in update_data and update_data["phone"] is not None:
        supplier.phone = update_data["phone"]

    if "address" in update_data and update_data["address"] is not None:
        supplier.address = update_data["address"]

    db.commit()
    db.refresh(supplier)

    log_audit(
        db,
        user_id=user_id,
        action="update_supplier",
        entity="supplier",
        entity_id=supplier.id,
    )
    db.commit()

    return supplier


def link_product_supplier(
    db: Session,
    product_id: int,
    supplier_id: int,
) -> ProductSupplier:
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise NotFoundError("Product not found")

    supplier = get_supplier(db, supplier_id)

    if supplier is None:
        raise NotFoundError("Supplier not found")

    existing = (
        db.query(ProductSupplier)
        .filter(
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == supplier_id,
        )
        .first()
    )

    if existing is not None:
        raise ConflictError("Product is already linked to this supplier")

    link = ProductSupplier(product_id=product_id, supplier_id=supplier_id)

    db.add(link)
    db.commit()
    db.refresh(link)

    return link


def get_product_suppliers(db: Session, product_id: int) -> list[ProductSupplier]:
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise NotFoundError("Product not found")

    return (
        db.query(ProductSupplier)
        .filter(ProductSupplier.product_id == product_id)
        .all()
    )


def get_supplier_products(db: Session, supplier_id: int) -> list[ProductSupplier]:
    supplier = get_supplier(db, supplier_id)

    if supplier is None:
        raise NotFoundError("Supplier not found")

    return (
        db.query(ProductSupplier)
        .filter(ProductSupplier.supplier_id == supplier_id)
        .all()
    )
