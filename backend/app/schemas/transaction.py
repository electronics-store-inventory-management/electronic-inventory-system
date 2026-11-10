from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InventoryTransactionBase(BaseModel):
    product_id: int = Field(..., gt=0)
    transaction_type: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=0)
    user_id: int = Field(..., gt=0)
    reference: str = Field(..., min_length=1)
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


class InventoryTransactionCreate(InventoryTransactionBase):
    pass


class InventoryTransactionResponse(InventoryTransactionBase):
    id: int
    date: datetime

    model_config = ConfigDict(from_attributes=True)
