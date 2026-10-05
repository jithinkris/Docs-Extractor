"""Pydantic models: the contract the LLM output must satisfy."""
from datetime import date
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

DocType = Literal["invoice", "receipt", "other"]

class LineItem(BaseModel):
    description: str
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Decimal

class Invoice(BaseModel):
    vendor_name: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Decimal

    @model_validator(mode="after")
    def totals_add_up(self):
        items = sum(i.amount for i in self.line_items)
        if self.line_items and self.subtotal is not None and abs(items - self.subtotal) > Decimal("0.02"):
            raise ValueError(f"line items sum {items} != subtotal {self.subtotal}")
        if self.subtotal is not None and self.tax is not None:
            if abs(self.subtotal + self.tax - self.total) > Decimal("0.02"):
                raise ValueError("subtotal + tax != total")
        return self
