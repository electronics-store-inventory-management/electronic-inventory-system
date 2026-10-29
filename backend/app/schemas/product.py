from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    quantity: int = Field(..., ge=0)
    # A threshold of zero means the product has no positive reorder threshold.
    min_stock_level: int = Field(default=0, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    category: str | None = Field(None, min_length=1, max_length=100)
    price: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    quantity: int | None = Field(None, ge=0)
    # Keep this optional so edits can change the threshold without changing other fields.
    min_stock_level: int | None = Field(None, ge=0)


class ProductResponse(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
