"""Rank collected fares and return the top-N cheapest results."""

from __future__ import annotations

from operator import attrgetter
from typing import Literal

from .models import Fare, SearchQuery, SearchResult


_SORT_KEYS: dict[str, str] = {
    "price": "price",
    "date": "departure_date",
    "duration": "duration_hours",
    "stops": "stops",
}


def select_cheapest(
    fares: list[Fare],
    query: SearchQuery,
) -> list[SearchResult]:
    """Sort *fares* according to *query.sort_by* and return the top N."""

    if not fares:
        return []

    filtered = _apply_stop_filter(fares, query.max_stops)
    key = _SORT_KEYS.get(query.sort_by, "price")
    filtered.sort(key=attrgetter(key))
    top = filtered[: query.top_n]
    return [SearchResult(rank=i + 1, fare=f) for i, f in enumerate(top)]


def _apply_stop_filter(fares: list[Fare], max_stops: int | None) -> list[Fare]:
    if max_stops is None:
        return list(fares)
    return [f for f in fares if f.stops <= max_stops]
