from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    quantity: int = Field(..., ge=0)

    @field_validator("name", "category")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("Invalid text")
        return value


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    category: str | None = Field(None, min_length=1, max_length=100)
    price: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    quantity: int | None = Field(None, ge=0)

    @field_validator("name", "category", "price", "quantity")
    @classmethod
    def reject_invalid_updates(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value or any(ord(c) < 32 for c in value):
                raise ValueError("Invalid text")
        return value


class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)