"""Shared fixtures for SearchFlights tests."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from searchflights.models import Fare, SearchQuery


@pytest.fixture
def sample_query() -> SearchQuery:
    return SearchQuery(
        origin="BOM",
        destinations=["CDG", "BKK"],
        window_start=date(2026, 6, 1),
        window_end=date(2026, 12, 31),
        trip_duration_min=7,
        trip_duration_max=10,
        top_n=5,
        currency="INR",
    )


@pytest.fixture
def sample_fares() -> list[Fare]:
    base = datetime(2026, 6, 1, 12, 0)
    return [
        Fare(origin="BOM", destination="CDG", departure_date=date(2026, 7, 10),
             return_date=date(2026, 7, 20), airline="Air France", stops=1,
             duration_hours=12.5, price=52000, collected_at=base),
        Fare(origin="BOM", destination="BKK", departure_date=date(2026, 8, 1),
             return_date=date(2026, 8, 11), airline="IndiGo", stops=0,
             duration_hours=4.5, price=18000, collected_at=base),
        Fare(origin="BOM", destination="CDG", departure_date=date(2026, 9, 5),
             return_date=date(2026, 9, 15), airline="Emirates", stops=1,
             duration_hours=14.0, price=45000, collected_at=base),
        Fare(origin="BOM", destination="BKK", departure_date=date(2026, 10, 3),
             return_date=date(2026, 10, 13), airline="Thai Airways", stops=0,
             duration_hours=4.0, price=21000, collected_at=base),
        Fare(origin="BOM", destination="CDG", departure_date=date(2026, 11, 1),
             return_date=date(2026, 11, 11), airline="Vistara", stops=1,
             duration_hours=13.0, price=48000, collected_at=base),
        Fare(origin="BOM", destination="BKK", departure_date=date(2026, 12, 20),
             return_date=date(2026, 12, 30), airline="IndiGo", stops=0,
             duration_hours=4.5, price=32000, collected_at=base),
    ]
