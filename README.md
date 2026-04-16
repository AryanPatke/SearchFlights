# SearchFlights

Find the cheapest round-trip flights within a date window by scanning Google Flights.

> **Disclaimer:** This tool automates browsing of Google Flights for **personal,
> non-commercial use only**. It may violate Google's Terms of Service. Use at
> your own risk. Keep rate limits conservative to minimise server impact.

## Features

- Scans Google Flights via headless Playwright browser for real, up-to-date fares.
- Searches across **multiple destinations** in a single run when no specific destination is given.
- Returns the **top-N cheapest round-trip flights** within your date window, sorted by price.
- Configurable trip duration, currency, max stops, and sort order.
- Output as a **Rich terminal table** or **structured JSON** -- optionally saved to a file.
- Includes a direct **booking link** for each result so you can go straight to Google Flights.
- Built with async Playwright, Pydantic models, and Click CLI for a clean, extensible codebase.

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/aryanpatke/SearchFlights.git && cd SearchFlights
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Install Playwright browsers (one-time)
playwright install chromium

# 3. Copy and adjust config
cp .env.example .env

# 4. Run a search
python3 -m searchflights \
    --origin BOM \
    --window 2026-04-10:2026-10-10

# Or with options
python3 -m searchflights \
    --origin BOM \
    --destination CDG \
    --window 2026-06-01:2026-12-31 \
    --top-n 5 \
    --format table \
    --output results.json
```

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--origin` | IATA departure airport code (required) | -- |
| `--destination` | IATA arrival airport code | Scans default list |
| `--window` | `YYYY-MM-DD:YYYY-MM-DD` date range | -- |
| `--top-n` | Number of cheapest results to return | `5` |
| `--trip-duration` | Return-trip length in days | `10` |
| `--currency` | ISO 4217 currency code | `INR` |
| `--stops` | Max stops: `0`, `1`, `2`, or `any` | `any` |
| `--sort` | Sort key: `price`, `date`, `duration`, `stops` | `price` |
| `--format` | Output format: `table` or `json` | `table` |
| `--output` | Write results to a file (in addition to stdout) | -- |
| `--verbose` | Enable verbose logging | off |

## Project Structure

```
src/searchflights/
├── __main__.py          # python -m entry point
├── cli.py               # Click commands
├── config.py            # Settings via pydantic-settings
├── planner.py           # Expands query into search tuples
├── collectors/
│   ├── base.py          # Abstract collector interface
│   └── google_flights.py
├── models.py            # Pydantic data models
├── evaluator.py         # Top-N cheapest ranking
└── formatter.py         # Table / JSON output
```

## Running Tests

```bash
pytest
```

## License

This project is licensed under the [MIT License](LICENSE).
