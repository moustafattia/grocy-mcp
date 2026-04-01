"""Typed models for testbed manifests, confirmations, outcomes, and reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TaskType = Literal["receipt_stock", "pantry_audit", "recipe_url_shopping"]
SupportedMode = Literal["cli", "mcp"]
SupportedSource = Literal["golden", "openai", "anthropic", "openai_compatible"]


def _normalize_text(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


class ScenarioManifest(BaseModel):
    id: str
    description: str
    seed_profile: Path
    task_type: TaskType
    input_asset: Path
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    golden_items_path: Path
    confirmation_path: Path
    expected_outcome_path: Path
    supported_modes: list[SupportedMode]
    supported_sources: list[SupportedSource]

    model_config = {"extra": "forbid"}

    @field_validator("id", "description")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _normalize_text(value)


class ProductResolution(BaseModel):
    input_index: int
    product: str

    model_config = {"extra": "forbid"}

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        return _normalize_text(value)


class ScenarioConfirmation(BaseModel):
    product_resolutions: list[ProductResolution] = Field(default_factory=list)
    shopping_list: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("shopping_list")
    @classmethod
    def validate_shopping_list(cls, value: str | None) -> str | None:
        return None if value is None else _normalize_text(value)


class ExpectedStockItem(BaseModel):
    product: str
    amount: float

    model_config = {"extra": "forbid"}

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        return _normalize_text(value)


class ExpectedShoppingItem(BaseModel):
    product: str
    amount: float
    note: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        return _normalize_text(value)


class ExpectedShoppingList(BaseModel):
    list_name: str
    items: list[ExpectedShoppingItem] = Field(default_factory=list)
    absent: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @field_validator("list_name")
    @classmethod
    def validate_list_name(cls, value: str) -> str:
        return _normalize_text(value)

    @field_validator("absent")
    @classmethod
    def validate_absent(cls, value: list[str]) -> list[str]:
        return [_normalize_text(item) for item in value]


class MutationExpectation(BaseModel):
    stock_changed: bool
    shopping_changed: bool

    model_config = {"extra": "forbid"}


class ExpectedOutcome(BaseModel):
    stock: list[ExpectedStockItem] = Field(default_factory=list)
    shopping_lists: list[ExpectedShoppingList] = Field(default_factory=list)
    mutations: MutationExpectation

    model_config = {"extra": "forbid"}


class RunReport(BaseModel):
    scenario_id: str
    mode: SupportedMode
    source: SupportedSource
    provider: str | None = None
    prompt_hash: str
    normalized_items: list[dict]
    preview_output: Any
    confirmation_actions: list[dict]
    apply_actions: list[dict]
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    assertions: list[dict]
    status: Literal["passed", "failed"]
    duration_ms: int

    model_config = {"extra": "forbid"}
