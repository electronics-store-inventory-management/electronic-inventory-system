from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryTransactionBase(BaseModel):
    product_id: int = Field(..., gt=0)
    transaction_type: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    reference: str = Field(..., min_length=1)
    date: datetime | None = None


class InventoryTransactionCreate(InventoryTransactionBase):
    pass


class InventoryTransactionResponse(InventoryTransactionBase):
    id: int
    date: datetime

    model_config = ConfigDict(from_attributes=True)
