"""Click CLI for SearchFlights."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

import click

from . import __version__
from .collectors.google_flights import GoogleFlightsCollector
from .evaluator import select_cheapest
from .formatter import format_results
from .models import SearchQuery
from .planner import plan_search

logger = logging.getLogger("searchflights")


def _parse_window(raw: str) -> tuple[date, date]:
    parts = raw.split(":")
    if len(parts) != 2:
        raise click.BadParameter("Window must be YYYY-MM-DD:YYYY-MM-DD")
    try:
        start = date.fromisoformat(parts[0])
        end = date.fromisoformat(parts[1])
    except ValueError as exc:
        raise click.BadParameter(f"Invalid date in window: {exc}") from exc
    if end <= start:
        raise click.BadParameter("Window end must be after start")
    if (end - start).days > 365:
        raise click.BadParameter("Window cannot exceed 12 months")
    return start, end


def _parse_stops(raw: str) -> int | None:
    if raw == "any":
        return None
    try:
        val = int(raw)
    except ValueError as exc:
        raise click.BadParameter("stops must be 0, 1, 2, or 'any'") from exc
    if val not in (0, 1, 2):
        raise click.BadParameter("stops must be 0, 1, 2, or 'any'")
    return val


@click.command(
    help=(
        "Find the cheapest round-trip flights within a date window.\n\n"
        "DISCLAIMER: This tool automates browsing of Google Flights for "
        "personal, non-commercial use only."
    ),
)
@click.option("--origin", required=True, help="IATA departure airport code (e.g. BOM).")
@click.option("--destination", default=None, help="IATA arrival airport code. Omit to scan popular destinations.")
@click.option("--window", required=True, help="Date range as YYYY-MM-DD:YYYY-MM-DD.")
@click.option("--top-n", default=5, show_default=True, type=int, help="Number of cheapest results to return.")
@click.option("--trip-duration", default=10, show_default=True, type=int, help="Return-trip length in days.")
@click.option("--currency", default="INR", show_default=True, help="ISO 4217 currency code.")
@click.option("--stops", default="any", show_default=True, help="Max stops: 0, 1, 2, or 'any'.")
@click.option("--sort", "sort_by", default="price", show_default=True, type=click.Choice(["price", "date", "duration", "stops"]))
@click.option("--format", "output_format", default="table", show_default=True, type=click.Choice(["table", "json"]))
@click.option("--output", "output_file", default=None, type=click.Path(), help="Write results to a file (in addition to stdout).")
@click.option("--verbose", is_flag=True, help="Enable verbose logging.")
@click.version_option(__version__)
def main(
    origin: str,
    destination: str | None,
    window: str,
    top_n: int,
    trip_duration: int,
    currency: str,
    stops: str,
    sort_by: str,
    output_format: str,
    output_file: str | None,
    verbose: bool,
) -> None:
    """Entry point for the CLI."""

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    window_start, window_end = _parse_window(window)
    max_stops = _parse_stops(stops)

    destinations: list[str] = []
    if destination:
        destinations = [d.strip().upper() for d in destination.split(",")]

    query = SearchQuery(
        origin=origin.upper(),
        destinations=destinations,
        window_start=window_start,
        window_end=window_end,
        trip_duration=trip_duration,
        top_n=top_n,
        currency=currency,
        max_stops=max_stops,
        sort_by=sort_by,
        output_format=output_format,
    )

    asyncio.run(_run(query, output_file))


async def _run(query: SearchQuery, output_file: str | None = None) -> None:
    legs = plan_search(query)
    logger.info("Planned %d search legs.", len(legs))

    all_fares = []
    successes = 0
    failures = 0

    async with GoogleFlightsCollector() as collector:
        for i, leg in enumerate(legs, 1):
            logger.info(
                "[%d/%d] %s -> %s  %s – %s",
                i, len(legs),
                leg.origin, leg.destination,
                leg.departure_date, leg.return_date,
            )
            fares = await collector.collect(leg)
            if fares:
                all_fares.extend(fares)
                successes += 1
            else:
                failures += 1

    logger.info(
        "Collection done: %d succeeded, %d failed, %d total fares.",
        successes, failures, len(all_fares),
    )

    results = select_cheapest(all_fares, query)
    format_results(results, query.output_format, total_legs=len(legs), output_file=output_file)
