# Flight Deals Service -- Product Requirements Document

**Version:** 0.1 (Draft)
**Date:** 2026-04-10
**Status:** Proposed

---

## 1. Problem Statement

Airfares between Indian cities and international destinations fluctuate significantly throughout the year. A traveller planning ahead (for example, "I want to fly from Mumbai somewhere in the next six months") has no easy way to scan a broad date window across many destinations and quickly isolate the dates and routes with the lowest available fares in that period.

Google Flights offers a powerful "Explore" view, but it still requires manual browsing, destination-by-destination comparison, and repeated date changes to find the cheapest opportunities. There is no simple way to ask for the cheapest round-trip options within a broad timeframe and get back a clean ranked list.

## 2. Target Users

| Persona | Description |
|---------|-------------|
| **Budget leisure traveller** | Flexible on dates and sometimes destinations; primarily wants the cheapest option within a window. |
| **Flexible fare shopper** | Knows the destination they want and wants the cheapest travel dates within a broad time window. |
| **Weekend explorer** | Based in a metro like Mumbai; looking for the cheapest short-haul options (Goa, Colombo, Bangkok) on upcoming weekends. |

All personas share one trait: they value **price over schedule precision** and are willing to be flexible to save money.

## 3. Goals and Non-Goals

### Goals (v1)

1. Accept a round-trip search query consisting of origin city, date window, optional destination filter, and an optional result-count limit.
2. Collect fare data from Google Flights (and potentially other public travel sources) for the specified query.
3. Return the cheapest round-trip flights found in the scanned window, sorted by total fare.
4. Present results in a clear, actionable format (CLI output and/or structured JSON).

### Non-Goals (v1)

- Building a web or mobile frontend.
- Booking or redirecting to booking flows.
- Real-time continuous monitoring or push notifications (future phase).
- Multi-city or complex itinerary support.
- Multi-passenger or premium-cabin searches (economy, single traveller only for now).
- Storing long-term historical price data for trend analysis (future phase).

### Success Metrics

| Metric | Target |
|--------|--------|
| Fare collection reliability | Successfully retrieve fares for >= 90% of queried route-date combinations per run. |
| Result relevance | Returned results are the lowest-priced valid itineraries found in the scanned set, correctly sorted by fare. |
| Latency | Full scan for a single origin over a 6-month window completes in < 10 minutes. |
| Usability | A new user can install, configure, and run their first search in < 5 minutes. |

## 4. User Stories and Example Scenarios

### US-1: Budget scan across destinations

> As a budget traveller based in Mumbai, I want to run a single command that checks round-trip flights from Mumbai to popular international destinations over the next 6 months and returns the 5 cheapest options overall, so I can quickly spot the best-value trips worth booking.

**Example:**

```
$ python -m searchflights \
    --origin BOM \
    --window 2026-04-10:2026-10-10 \
    --top-n 5 \
    --currency INR
```

Output (illustrative):

```
 Route           Dates                  Price (INR)  Airline
 BOM -> CMB      May 03 – May 13        12,200       SriLankan
 BOM -> BKK      Jul 12 – Jul 22        18,450       IndiGo
 BOM -> KUL      Aug 22 – Sep 01        22,800       AirAsia
 BOM -> SGN      Sep 04 – Sep 14        23,600       VietJet Air
 BOM -> HKT      Oct 11 – Oct 21        24,150       Thai AirAsia
 5 cheapest options returned (47 routes checked)
```

### US-2: Destination-specific watch

> As a traveller who wants to visit Paris, I want to see the cheapest Mumbai-to-Paris round-trip options between June and December so I can choose the best dates.

```
$ python -m searchflights \
    --origin BOM \
    --destination CDG \
    --window 2026-06-01:2026-12-31 \
    --top-n 5
```

### US-3: JSON output for downstream tooling

> As a developer, I want structured JSON output so I can pipe results into a notification script or dashboard.

```
$ python -m searchflights ... --format json
```

## 5. Functional Requirements

### 5.1 Search Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `origin` | Yes | IATA code of the departure airport (e.g., `BOM`). |
| `destination` | No | IATA code of arrival airport. If omitted, scan a configurable list of popular destinations and return the cheapest results overall across all scanned destinations. |
| `window` | Yes | Date range in `YYYY-MM-DD:YYYY-MM-DD` format. Maximum span: 12 months. |
| `top_n` | No | Number of cheapest round-trip results to return. Default: `5`. Recommended range: `3-10`. |
| `currency` | No | ISO 4217 currency code. Default: `INR`. |
| `trip_duration` | No | Return-trip length in days. Default: `10`. Future versions may support ranges. |
| `stops` | No | Maximum number of stops. Default: any. Options: `0` (non-stop), `1`, `2`, `any`. |
| `format` | No | Output format. `table` (default) or `json`. |

### 5.2 Fare Collection

- **Primary source:** Google Flights (`https://www.google.com/travel/flights`), accessed via browser automation (Playwright / Selenium) to render the JavaScript-heavy UI.
- **Fallback / supplementary sources:** Consider scraping alternative aggregators or using publicly available flight-data APIs if Google Flights becomes unreliable for a particular query.
- **Collection strategy:** For each origin-destination pair, iterate over departure dates within the window using a configurable step (default: weekly). For each departure date, search the matching return date using the configured `trip_duration` offset. In v1, this defaults to 10 days after departure.
- **Rate limiting:** Introduce configurable delays between requests (default: 2-5 seconds random jitter) to reduce the risk of being blocked.
- **Data extracted per fare option:** airline(s), departure/arrival times, number of stops, total duration, round-trip price, booking deeplink (if available).

### 5.3 Cheapest-Flight Selection

In v1, the system does not compare fares against historical norms or user thresholds. Instead it:

1. Collects all valid round-trip itineraries found for the scanned query set.
2. Sorts them by total round-trip price ascending.
3. Returns the top `N` cheapest results, where `N` defaults to `5`.

If no destination is provided, ranking happens across all scanned destinations combined, not per destination.

### 5.4 Result Ranking

Results are sorted by **price ascending** by default. Alternative sort keys (date, duration, number of stops) can be specified via `--sort`, but the default product behavior is to return the cheapest options first.

### 5.5 Response Format

- **Table (default):** Human-readable ASCII table printed to stdout.
- **JSON:** Array of result objects written to stdout, suitable for piping.

Each result object contains:

```json
{
  "origin": "BOM",
  "destination": "CDG",
  "departure_date": "2026-07-12",
  "return_date": "2026-07-19",
  "airline": "Air France",
  "stops": 1,
  "duration_hours": 12.5,
  "price": 42000,
  "currency": "INR",
  "source": "google_flights",
  "collected_at": "2026-04-10T14:22:00Z"
}
```

## 6. Data-Source Strategy and Constraints

### 6.1 Google Flights Scraping

Google Flights is a JavaScript-rendered single-page application. Reliable data extraction requires:

- **Headless browser automation** using Playwright (preferred for its async support and Chromium/Firefox/WebKit coverage) or Selenium as a fallback.
- **Selectors strategy:** Use `aria` and `data-*` attribute selectors where possible; fall back to CSS class selectors with version-pinned snapshots so selector drift is detected early.
- **Anti-bot mitigation:** Random delays, realistic viewport sizes, user-agent rotation, and optional proxy support. Google may still block or CAPTCHA automated traffic; the system should detect this and log a clear warning rather than returning stale/empty results.

### 6.2 Compliance Considerations

- Google's Terms of Service prohibit automated scraping. This tool is intended for **personal, non-commercial use** and should be documented as such.
- The PRD recommends adding a clear disclaimer in the README and CLI `--help` output.
- Rate-limit defaults should be conservative to minimize server impact.

### 6.3 Source Reliability

Scraping is inherently fragile. The system should:

- Log every request and its outcome (success / empty / blocked / error).
- Surface a per-run summary of collection health (e.g., "47/50 queries succeeded").
- Make it straightforward to swap in or add alternative sources behind a common adapter interface.

## 7. Architecture Overview

```
┌─────────────┐
│   CLI / API  │   User-facing entry point (Click / argparse)
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│  Search Planner  │   Expands user query into (origin, dest, date) tuples
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Fare Collector  │   Drives headless browser, extracts raw fare data
│  (Playwright)    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Normalizer      │   Cleans, deduplicates, converts currencies
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Cheapest Selector│   Ranks itineraries and returns top-N cheapest results
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Formatter       │   Renders results as table or JSON
└─────────────────┘
```

### Technology Choices (v1)

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.11+ | Mature ecosystem for scraping, async I/O, and CLI tooling. |
| Browser automation | Playwright (`playwright` PyPI package) | Async-native, multi-browser, well-maintained. |
| CLI framework | `click` | Cleaner than argparse for multi-option commands. |
| HTTP (supplementary) | `httpx` | Async HTTP client for non-browser sources. |
| Data modelling | `pydantic` | Validate and serialize fare/result objects. |
| Table rendering | `rich` | Beautiful terminal tables with minimal code. |
| Config | `pydantic-settings` + `.env` file | Manage defaults, proxy config, delays, destination lists. |
| Packaging | `pyproject.toml` + `pip` | Standard Python packaging. |
| Testing | `pytest` + `pytest-asyncio` | Unit and integration tests. |

### Proposed Project Layout

```
SearchFlights/
├── docs/
│   └── prd.md                  # This document
├── src/
│   └── searchflights/
│       ├── __init__.py
│       ├── __main__.py          # CLI entry point
│       ├── cli.py               # Click command definitions
│       ├── config.py            # Settings and defaults
│       ├── planner.py           # Query expansion logic
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract collector interface
│       │   └── google_flights.py
│       ├── models.py            # Pydantic models (Fare, SearchResult, SearchQuery)
│       ├── evaluator.py         # Cheapest-flight ranking logic
│       └── formatter.py         # Table / JSON output
├── tests/
│   ├── conftest.py
│   ├── test_planner.py
│   ├── test_evaluator.py
│   └── test_formatter.py
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

## 8. Non-Functional Requirements

| Requirement | Detail |
|-------------|--------|
| **Portability** | Must run on Linux, macOS, and Windows with Python 3.11+. |
| **Extensibility** | New fare sources added by implementing a `BaseCollector` interface; no changes to ranking logic or CLI. |
| **Logging** | Structured logging via Python `logging`; configurable verbosity (`--verbose` / `--quiet`). |
| **Error handling** | Graceful degradation: if a single route query fails, log the error and continue with remaining queries. |
| **Security** | No credentials stored in code. Proxy credentials and API keys (future) loaded from environment variables or `.env`. |

## 9. Risks and Assumptions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google blocks automated requests (CAPTCHA, IP ban). | High | Fare collection fails partially or fully. | Rate limiting, user-agent rotation, proxy support, fallback sources. |
| Google Flights DOM structure changes without notice. | Medium | Selectors break; no data extracted. | Selector versioning, integration tests against snapshots, monitoring. |
| Prices shown to headless browser differ from real user prices. | Low-Medium | Deals may not match what the user sees on Google Flights. | Document this limitation; let users verify via the provided deeplink. |
| Legal/ToS risk from scraping Google Flights. | Medium | Potential cease-and-desist. | Personal-use disclaimer; keep rate limits conservative; consider API alternatives long-term. |

### Assumptions

1. The user has a stable internet connection and can install Playwright browsers locally.
2. Google Flights will continue to render fare results client-side in a scrapeable DOM structure.
3. INR is the default currency, but the system should support other currencies via Google Flights' built-in currency selector.
4. Round-trip fares are the primary comparison unit, with a default return date 10 days after departure unless overridden.
5. One adult, economy class for v1.

## 10. Phased Roadmap

### Phase 1 -- Prototype (current)

- CLI tool that accepts origin, window, optional destination, optional `top_n`, and an optional return-trip length with a default of 10 days.
- Google Flights scraping via Playwright with basic anti-bot measures.
- Top-5-cheapest selection logic across the scanned result set.
- Table and JSON output.
- Manual invocation only.

### Phase 2 -- Robustness

- Selector health checks and integration test suite against saved page snapshots.
- Proxy and user-agent pool configuration.
- Lightweight SQLite storage of collected fares for within-session deduplication and optional cross-run comparison.
- Better destination-list management and optional filters for stops, airlines, and trip duration presets.

### Phase 3 -- Intelligence

- Historical fare storage for optional trend insights and price calendars.
- Optional richer scoring or price-history overlays for users who want more than pure cheapest-first ranking.
- Scheduled runs (cron / systemd timer) with diff-based notifications (email, Telegram, Slack webhook).

### Phase 4 -- Scale and UX

- REST API layer (FastAPI) for integration with dashboards or mobile apps.
- Multi-origin, multi-passenger, premium-cabin support.
- Alternative data sources behind the collector adapter interface (Skyscanner, Kayak, Kiwi API).
- Web frontend for interactive exploration.

---

*End of PRD v0.1*
