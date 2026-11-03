from pydantic import BaseModel, ConfigDict


class LowStockProduct(BaseModel):
    id: int
    name: str
    quantity: int
    min_stock_level: int


class InventoryReport(BaseModel):
    products: list[LowStockProduct]
    low_stock: list[LowStockProduct]

    model_config = ConfigDict(from_attributes=True)
