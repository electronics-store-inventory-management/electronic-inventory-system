from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.database.database import SessionLocal
from app.models.product import Product
from app.models.supplier import ProductSupplier, Supplier
from app.schemas.supplier import (
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.supplier_service import (
    create_supplier,
    get_supplier,
    get_supplier_products,
    get_suppliers,
    link_product_supplier,
    update_supplier,
)

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_supplier(
    supplier_data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    return create_supplier(db, supplier_data, current_user["id"])


@router.get(
    "/",
    response_model=list[SupplierResponse],
)
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_suppliers(db)


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
)
def view_supplier(
    supplier_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    supplier = get_supplier(db, supplier_id)

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )

    return supplier


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
)
def update_supplier_details(
    supplier_id: int = Path(..., gt=0),
    supplier_data: SupplierUpdate = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    supplier = update_supplier(db, supplier_id, supplier_data, current_user["id"])

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )

    return supplier


@router.post(
    "/{supplier_id}/products/{product_id}",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def link_product_to_supplier(
    supplier_id: int = Path(..., gt=0),
    product_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    supplier = get_supplier(db, supplier_id)

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )

    link_product_supplier(db, product_id, supplier_id)

    return {"message": "Product linked to supplier"}


@router.get(
    "/{supplier_id}/products",
    response_model=list[dict],
)
def list_supplier_products(
    supplier_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    supplier = get_supplier(db, supplier_id)

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )

    links = get_supplier_products(db, supplier_id)

    return [
        {
            "id": link.id,
            "product_id": link.product_id,
            "supplier_id": link.supplier_id,
        }
        for link in links
    ]
