"""Pydantic models for search queries, collected fares, and ranked results."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """User-facing search parameters after CLI parsing."""

    origin: str = Field(..., min_length=2, description="IATA code or city name")
    destinations: list[str] = Field(
        default_factory=list,
        description="IATA codes or city names; empty means use the default list",
    )
    window_start: date
    window_end: date
    trip_duration_min: int = Field(default=7, ge=1, le=90)
    trip_duration_max: int = Field(default=10, ge=1, le=90)
    top_n: int = Field(default=5, ge=1, le=50)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    max_stops: int | None = Field(
        default=None, description="None means any number of stops"
    )
    sort_by: Literal["price", "date", "duration", "stops"] = "price"
    output_format: Literal["table", "json"] = "json"


class SearchLeg(BaseModel):
    """A single (origin, destination, departure_date, return_date) to query."""

    origin: str
    destination: str
    departure_date: date
    return_date: date
    currency: str = "INR"


class Fare(BaseModel):
    """A single fare option extracted from a source."""

    origin: str
    destination: str
    departure_date: date
    return_date: date
    airline: str = "N/A"
    stops: int = 0
    duration_hours: float = 0.0
    price: float
    currency: str = "INR"
    source: str = "google_flights"
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    booking_url: str = ""


class SearchResult(BaseModel):
    """A ranked fare returned to the user."""

    rank: int
    fare: Fare
