from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId

class Product(BaseModel):
    product_id: str = Field(..., example="P12345")  # Unique identifier
    owner_id: str = Field(..., example="U67890")  # Reference to the user
    product_name: str = Field(..., example="Laptop")
    category: Optional[str] = Field(None, example="Electronics")
    price: float = Field(..., example=50000.00)
    stock: Optional[int] = Field(0, example=10)  # Available stock
    description: Optional[str] = Field(None, example="Gaming Laptop with RTX 3070")

    class Config:
        orm_mode = True