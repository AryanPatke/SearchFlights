"""Expand a SearchQuery into concrete SearchLeg instances to query."""

from __future__ import annotations

from datetime import timedelta

from .config import settings
from .models import SearchLeg, SearchQuery


def plan_search(query: SearchQuery) -> list[SearchLeg]:
    """Return a list of (origin, dest, depart, return) legs to scrape."""

    destinations = query.destinations or settings.default_destinations

    legs: list[SearchLeg] = []
    for dest in destinations:
        dep = query.window_start
        while dep <= query.window_end:
            ret = dep + timedelta(days=query.trip_duration)
            legs.append(
                SearchLeg(
                    origin=query.origin,
                    destination=dest,
                    departure_date=dep,
                    return_date=ret,
                    currency=query.currency,
                )
            )
            dep += timedelta(days=settings.date_step_days)

    return legs
