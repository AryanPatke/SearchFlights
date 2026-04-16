"""Tests for the cheapest-flight evaluator."""

from __future__ import annotations

from datetime import date

from searchflights.evaluator import select_cheapest
from searchflights.models import Fare, SearchQuery


def test_returns_top_n_cheapest(sample_query, sample_fares):
    results = select_cheapest(sample_fares, sample_query)

    assert len(results) == sample_query.top_n
    prices = [r.fare.price for r in results]
    assert prices == sorted(prices)
    assert prices[0] == 18000


def test_respects_top_n_limit(sample_query, sample_fares):
    sample_query.top_n = 2
    results = select_cheapest(sample_fares, sample_query)
    assert len(results) == 2
    assert results[0].fare.price == 18000
    assert results[1].fare.price == 21000


def test_ranks_start_at_one(sample_query, sample_fares):
    results = select_cheapest(sample_fares, sample_query)
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(results) + 1))


def test_stop_filter(sample_query, sample_fares):
    sample_query.max_stops = 0
    results = select_cheapest(sample_fares, sample_query)
    assert all(r.fare.stops == 0 for r in results)


def test_empty_fares(sample_query):
    results = select_cheapest([], sample_query)
    assert results == []


def test_sort_by_date(sample_query, sample_fares):
    sample_query.sort_by = "date"
    results = select_cheapest(sample_fares, sample_query)
    dates = [r.fare.departure_date for r in results]
    assert dates == sorted(dates)
