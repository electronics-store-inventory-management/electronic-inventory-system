from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.database.database import SessionLocal
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.report import LowStockProduct
from app.services.report_service import (
    get_low_stock_products as get_low_stock_report,
)
from app.services.product_service import (
    create_product,
    get_product,
    get_products,
    update_product,
    delete_product,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=201,
)
def add_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    return create_product(db, product_data, user_id=current_user["id"])


@router.get(
    "/",
    response_model=list[ProductResponse],
)
def search_products(
    name: str | None = Query(default=None),
    category: str | None = Query(default=None),
    product_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_products(
        db,
        name=name,
        category=category,
        product_id=product_id,
    )


@router.get(
    "/low-stock",
    response_model=list[LowStockProduct],
)
def list_low_stock_products(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """List products with less stock than their configured minimum level."""
    return get_low_stock_report(db)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def view_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    product = get_product(db, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product_details(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    product = update_product(
        db,
        product_id,
        product_data,
        user_id=current_user["id"],
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
)
def remove_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    product = delete_product(db, product_id, user_id=current_user["id"])

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product