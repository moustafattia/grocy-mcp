"""Pydantic models for Grocy API entities."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    name: str
    description: str | None = None
    location_id: int | None = None
    min_stock_amount: float = 0
    qu_id_purchase: int | None = None
    qu_id_stock: int | None = None

    model_config = {"extra": "allow"}


class ProductBarcode(BaseModel):
    id: int
    product_id: int
    barcode: str
    qu_id: int | None = None
    amount: float | None = None

    model_config = {"extra": "allow"}


class StockEntry(BaseModel):
    id: int
    product_id: int
    amount: float
    best_before_date: str | None = None
    location_id: int | None = None
    open: int = 0
    price: float | None = None

    model_config = {"extra": "allow"}


class ShoppingListItem(BaseModel):
    id: int
    shopping_list_id: int = 1
    product_id: int | None = None
    amount: float = 1
    note: str | None = None
    done: int = 0

    model_config = {"extra": "allow"}


class RecipeIngredient(BaseModel):
    id: int
    recipe_id: int
    product_id: int
    amount: float = 1
    qu_id: int | None = None
    note: str | None = None

    model_config = {"extra": "allow"}


class Recipe(BaseModel):
    id: int
    name: str
    description: str | None = None
    instructions: str | None = None
    base_servings: int = Field(default=1, alias="base_servings")
    ingredients: list[RecipeIngredient] = []

    model_config = {"extra": "allow", "populate_by_name": True}


class Chore(BaseModel):
    id: int
    name: str
    period_type: str | None = None
    period_interval: int | None = None
    next_execution_assigned_to_user_id: int | None = None
    next_estimated_execution_time: datetime | None = None

    model_config = {"extra": "allow"}


class ChoreExecution(BaseModel):
    id: int
    chore_id: int
    executed_time: datetime
    done_by_user_id: int | None = None

    model_config = {"extra": "allow"}


class SystemInfo(BaseModel):
    grocy_version: dict
    php_version: str
    sqlite_version: str
    os: str

    model_config = {"extra": "allow"}
