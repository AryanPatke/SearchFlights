"""Render search results as a Rich table or JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .models import SearchResult


def format_results(
    results: list[SearchResult],
    output_format: str = "table",
    total_legs: int = 0,
    output_file: str | None = None,
) -> None:
    """Print *results* to stdout and optionally write to a file."""

    if output_format == "json":
        _print_json(results)
    else:
        _print_table(results, total_legs)

    if output_file:
        _write_file(results, output_format, total_legs, output_file)


def _print_table(results: list[SearchResult], total_legs: int) -> None:
    console = Console()

    if not results:
        console.print("[bold red]No results found.[/bold red]")
        return

    table = Table(
        title="Cheapest Flights",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", width=3)
    table.add_column("Route", min_width=14)
    table.add_column("Dates", min_width=24)
    table.add_column("Airline", min_width=14)
    table.add_column("Stops", justify="center", width=5)
    table.add_column("Duration", justify="right", min_width=8)
    table.add_column("Price", justify="right", min_width=10)

    for r in results:
        f = r.fare
        route = f"{f.origin} -> {f.destination}"
        dates = f"{f.departure_date:%b %d} – {f.return_date:%b %d}"
        duration = f"{f.duration_hours:.1f} h" if f.duration_hours else "—"
        price = f"{f.currency} {f.price:,.0f}"
        table.add_row(
            str(r.rank), route, dates, f.airline,
            str(f.stops), duration, price,
        )

    console.print(table)

    has_urls = any(r.fare.booking_url for r in results)
    if has_urls:
        console.print("\n[bold]Booking links:[/bold]")
        for r in results:
            if r.fare.booking_url:
                console.print(
                    f"  {r.rank}. [link={r.fare.booking_url}]{r.fare.booking_url}[/link]"
                )

    summary = f"{len(results)} cheapest option(s) returned"
    if total_legs:
        summary += f" ({total_legs} route-dates checked)"
    console.print(f"\n[dim]{summary}[/dim]")


def _print_json(results: list[SearchResult]) -> None:
    data = _results_to_dicts(results)
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _results_to_dicts(results: list[SearchResult]) -> list[dict]:
    return [
        {"rank": r.rank, **r.fare.model_dump(mode="json")}
        for r in results
    ]


def _write_file(
    results: list[SearchResult],
    output_format: str,
    total_legs: int,
    path: str,
) -> None:
    console = Console(stderr=True)
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "json" or filepath.suffix == ".json":
        data = _results_to_dicts(results)
        filepath.write_text(json.dumps(data, indent=2, default=str) + "\n")
    else:
        lines: list[str] = []
        lines.append(
            f"{'#':<4} {'Route':<16} {'Dates':<26} {'Airline':<20} "
            f"{'Stops':<6} {'Duration':<10} {'Price':<12}"
        )
        lines.append("-" * 96)
        for r in results:
            f = r.fare
            route = f"{f.origin} -> {f.destination}"
            dates = f"{f.departure_date:%b %d} – {f.return_date:%b %d}"
            duration = f"{f.duration_hours:.1f} h" if f.duration_hours else "—"
            price = f"{f.currency} {f.price:,.0f}"
            lines.append(
                f"{r.rank:<4} {route:<16} {dates:<26} {f.airline:<20} "
                f"{f.stops:<6} {duration:<10} {price:<12}"
            )
        has_urls = any(r.fare.booking_url for r in results)
        if has_urls:
            lines.append("")
            lines.append("Booking links:")
            for r in results:
                if r.fare.booking_url:
                    lines.append(f"  {r.rank}. {r.fare.booking_url}")
        lines.append("")
        summary = f"{len(results)} cheapest option(s) returned"
        if total_legs:
            summary += f" ({total_legs} route-dates checked)"
        lines.append(summary)
        filepath.write_text("\n".join(lines) + "\n")

    console.print(f"[green]Results written to {filepath}[/green]")
