# -*- coding: utf-8 -*-
"""System-wide favorites endpoints (anonymous user shared)."""

from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from src.storage import DatabaseManager

router = APIRouter()


class FavoriteRequest(BaseModel):
    """Add favorite request body."""

    model_config = {"populate_by_name": True}

    code: str = Field(..., description="Stock or ETF code")
    type: str = Field(..., alias="type", description="'stock' or 'etf'")


class FavoritesResponse(BaseModel):
    """Favorites list response."""

    stocks: list[str] = Field(default_factory=list)
    etfs: list[str] = Field(default_factory=list)


@router.get(
    "",
    response_model=FavoritesResponse,
    summary="Get all favorites",
)
def get_favorites() -> FavoritesResponse:
    """Return system-wide favorites (shared by all anonymous users)."""
    db = DatabaseManager.get_instance()
    return FavoritesResponse(
        stocks=db.get_favorites("stock"),
        etfs=db.get_favorites("etf"),
    )


@router.post(
    "",
    status_code=201,
    summary="Add a favorite",
)
def add_favorite(body: FavoriteRequest) -> dict:
    """Add a stock or ETF to system-wide favorites."""
    db = DatabaseManager.get_instance()
    db.add_favorite(body.code, body.type)
    return {"ok": True}


@router.delete(
    "/{code}",
    summary="Remove a favorite",
)
def remove_favorite(code: str, type: str = "stock") -> Response:
    """Remove a stock or ETF from system-wide favorites."""
    db = DatabaseManager.get_instance()
    db.remove_favorite(code, type)
    return Response(status_code=204)