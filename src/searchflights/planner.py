"""Expand a SearchQuery into concrete SearchLeg instances to query."""

from __future__ import annotations

from datetime import timedelta

from .config import settings
from .models import SearchLeg, SearchQuery


def plan_search(
    query: SearchQuery,
    date_step_override: int | None = None,
) -> list[SearchLeg]:
    """Return a list of (origin, dest, depart, return) legs to scrape.

    For each departure date, generates legs for the min and max trip
    durations (and skips duplicates when they are equal).
    """

    destinations = query.destinations or settings.default_destinations
    step = date_step_override or settings.date_step_days

    durations = sorted({query.trip_duration_min, query.trip_duration_max})

    legs: list[SearchLeg] = []
    for dest in destinations:
        dep = query.window_start
        while dep <= query.window_end:
            for dur in durations:
                ret = dep + timedelta(days=dur)
                legs.append(
                    SearchLeg(
                        origin=query.origin,
                        destination=dest,
                        departure_date=dep,
                        return_date=ret,
                        currency=query.currency,
                    )
                )
            dep += timedelta(days=step)

    return legs
