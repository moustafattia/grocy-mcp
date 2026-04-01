"""Stable workflow-oriented data contracts for preview/apply flows."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _normalize_optional_text(value: str | None) -> str | None:
    """Collapse whitespace and normalize empty strings to None."""
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


class WorkflowPreviewCandidate(BaseModel):
    product_id: int
    name: str

    model_config = {"extra": "forbid"}


class WorkflowNormalizedInputItem(BaseModel):
    label: str
    quantity: float = 1.0
    unit_text: str | None = None
    barcode: str | None = None
    note: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("label must not be empty")
        return normalized

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("quantity must be greater than 0")
        return value

    @field_validator("unit_text", "barcode", "note")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class WorkflowMatchPreviewItem(BaseModel):
    input_index: int
    label: str
    status: Literal["matched", "ambiguous", "unmatched"]
    matched_product_id: int | None = None
    matched_product_name: str | None = None
    candidates: list[WorkflowPreviewCandidate] = Field(default_factory=list)
    suggested_amount: float
    unit_text: str | None = None

    model_config = {"extra": "forbid"}


class WorkflowApplyItem(BaseModel):
    product_id: int
    amount: float
    note: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("amount must be greater than 0")
        return value

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class WorkflowShoppingReconcilePreviewAction(BaseModel):
    shopping_item_id: int
    action: Literal["remove", "set_amount"]
    previous_amount: float
    new_amount: float | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_action(self) -> WorkflowShoppingReconcilePreviewAction:
        if self.action == "set_amount":
            if self.new_amount is None:
                raise ValueError("new_amount is required when action is set_amount")
            if self.new_amount <= 0:
                raise ValueError("new_amount must be greater than 0 when action is set_amount")
        return self


class WorkflowShoppingReconcilePreviewItem(BaseModel):
    input_index: int
    product_id: int
    purchased_amount: float
    status: Literal["matched", "partial", "unmatched"]
    actions: list[WorkflowShoppingReconcilePreviewAction] = Field(default_factory=list)
    unapplied_amount: float = 0

    model_config = {"extra": "forbid"}


class WorkflowShoppingReconcileApplyAction(BaseModel):
    shopping_item_id: int
    action: Literal["remove", "set_amount"]
    new_amount: float | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_action(self) -> WorkflowShoppingReconcileApplyAction:
        if self.action == "set_amount":
            if self.new_amount is None:
                raise ValueError("new_amount is required when action is set_amount")
            if self.new_amount <= 0:
                raise ValueError("new_amount must be greater than 0 when action is set_amount")
        return self
