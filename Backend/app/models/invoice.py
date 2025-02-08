from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date

class InvoiceProduct(BaseModel):
    product_name: str = Field(..., example="Sugar")
    product_code: Optional[str] = Field(None, example="P12345")
    category: Optional[str] = Field(None, example="Groceries")
    quantity: int = Field(..., example=1)
    unit_price: float = Field(..., example=240.00)
    total_price: float = Field(..., example=240.00)
    tax: Optional[float] = Field(None, example=0.00)
    discount: Optional[float] = Field(None, example=0.00)

    class Config:
        orm_mode = True

class Invoice(BaseModel):
    invoice_number: Optional[str] = Field(None, example="INV-1001")
    invoice_date: Optional[date] = Field(None, example="2024-02-02")
    due_date: Optional[date] = Field(None, example="2024-02-10")

    seller_name: str = Field(..., example="Guru Krupa Trades")
    seller_address: Optional[str] = Field(None, example="meri-link road 18 Sector Nothik")

    buyer_name: Optional[str] = Field(None, example="John Doe")
    buyer_address: Optional[str] = Field(None, example="123 Main Street, City")

    product_items: List[InvoiceProduct]  # List of purchased products

    subtotal: Optional[float] = Field(None, example=1580.00)
    tax_amount: Optional[float] = Field(None, example=0.00)
    shipping_cost: Optional[float] = Field(None, example=50.00)
    total_amount: float = Field(..., example=1580.00)

    payment_method: Optional[str] = Field(None, example="Credit Card")
    currency: Optional[str] = Field(None, example="INR")

    order_status: Optional[str] = Field(None, example="Pending")
    payment_status: Optional[str] = Field(None, example="Unpaid")
    payment_due_date: Optional[date] = Field(None, example="2024-02-15")
    transaction_id: Optional[str] = Field(None, example="TXN-98765")

    invoice_terms: Optional[str] = Field(None, example="Net 30 days")
    shipping_address: Optional[str] = Field(None, example="456 Shipping Lane, City")
    billing_address: Optional[str] = Field(None, example="123 Billing St, City")

    invoice_type: Optional[str] = Field(None, example="Retail")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
