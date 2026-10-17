"""Validate the snapshot before using it for finance calculations."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Invoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    customer: str = Field(min_length=1, max_length=160)
    segment: str = Field(min_length=1, max_length=160)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    due: date
    previous_invoices: int = Field(ge=0, le=1000000)
    late_payments: int = Field(ge=0, le=1000000)
    broken_promises: int = Field(ge=0, le=1000000)
    disputed: bool

    @model_validator(mode="after")
    def consistent_history(self):
        if self.late_payments > self.previous_invoices:
            raise ValueError("late_payments cannot exceed previous_invoices")
        return self


class ReceivablesSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: date
    currency: Literal["USD"]
    invoices: list[Invoice] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_invoice_ids(self):
        ids = [invoice.id for invoice in self.invoices]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate invoice IDs found; correct the source snapshot")
        return self
