from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InventoryTransactionBase(BaseModel):
    product_id: int = Field(..., gt=0)
    transaction_type: Literal["ADD", "DEDUCT", "SET"]
    quantity: int = Field(..., ge=0)
    user_id: int = Field(..., gt=0)
    reference: str = Field(..., min_length=1, max_length=100)
    date: datetime | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int, info):
        transaction_type = info.data.get("transaction_type")
        if transaction_type == "SET":
            return value
        if value <= 0:
            raise ValueError("Quantity must be greater than zero")
        return value

    @field_validator("reference")
    @classmethod
    def validate_reference(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("Invalid reference")
        return value


class InventoryTransactionCreate(InventoryTransactionBase):
    pass


class InventoryTransactionResponse(InventoryTransactionBase):
    id: int
    date: datetime
    model_config = ConfigDict(from_attributes=True)
