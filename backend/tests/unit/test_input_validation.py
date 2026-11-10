import pytest
from pydantic import ValidationError

from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.transaction import InventoryTransactionCreate
from app.schemas.supplier import SupplierCreate


def test_reject_blank_product_name():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="   ",
            category="Electronics",
            price=100,
            quantity=10,
        )


def test_reject_blank_product_category():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Laptop",
            category="   ",
            price=100,
            quantity=10,
        )


def test_reject_negative_product_quantity():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Laptop",
            category="Electronics",
            price=100,
            quantity=-1,
        )


def test_reject_null_product_update():
    with pytest.raises(ValidationError):
        ProductUpdate(name=None)


def test_reject_invalid_transaction_type():
    with pytest.raises(ValidationError):
        InventoryTransactionCreate(
            product_id=1,
            transaction_type="DELETE",
            quantity=2,
            user_id=1,
            reference="Test",
        )


def test_reject_blank_transaction_reference():
    with pytest.raises(ValidationError):
        InventoryTransactionCreate(
            product_id=1,
            transaction_type="ADD",
            quantity=2,
            user_id=1,
            reference="   ",
        )


def test_reject_invalid_supplier_email():
    with pytest.raises(ValidationError):
        SupplierCreate(
            name="Supplier",
            email="invalid-email",
        )


def test_reject_blank_supplier_name():
    with pytest.raises(ValidationError):
        SupplierCreate(name="   ")