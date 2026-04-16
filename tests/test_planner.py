"""Tests for the search planner."""

from __future__ import annotations

from datetime import date, timedelta

from searchflights.models import SearchQuery
from searchflights.planner import plan_search


def test_plan_single_destination_weekly_steps():
    query = SearchQuery(
        origin="BOM",
        destinations=["CDG"],
        window_start=date(2026, 7, 1),
        window_end=date(2026, 7, 28),
        trip_duration=10,
    )
    legs = plan_search(query)

    assert len(legs) >= 4
    assert all(l.origin == "BOM" and l.destination == "CDG" for l in legs)
    for l in legs:
        assert l.return_date == l.departure_date + timedelta(days=10)


def test_plan_multiple_destinations():
    query = SearchQuery(
        origin="BOM",
        destinations=["CDG", "BKK", "SIN"],
        window_start=date(2026, 7, 1),
        window_end=date(2026, 7, 14),
        trip_duration=10,
    )
    legs = plan_search(query)
    dests = {l.destination for l in legs}
    assert dests == {"CDG", "BKK", "SIN"}


def test_plan_uses_default_destinations_when_empty(monkeypatch):
    from searchflights import config

    monkeypatch.setattr(config.settings, "default_destinations_csv", "LHR,NRT")
    # Clear the cached_property so it re-parses the CSV.
    config.settings.__dict__.pop("default_destinations", None)

    query = SearchQuery(
        origin="BOM",
        destinations=[],
        window_start=date(2026, 7, 1),
        window_end=date(2026, 7, 7),
        trip_duration=10,
    )
    legs = plan_search(query)
    dests = {l.destination for l in legs}
    assert dests == {"LHR", "NRT"}


def test_plan_empty_window():
    query = SearchQuery(
        origin="BOM",
        destinations=["CDG"],
        window_start=date(2026, 7, 10),
        window_end=date(2026, 7, 5),
        trip_duration=10,
    )
    legs = plan_search(query)
    assert legs == []
