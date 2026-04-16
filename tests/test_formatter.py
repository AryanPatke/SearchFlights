"""Tests for the output formatter."""

from __future__ import annotations

import json
from io import StringIO

from searchflights.formatter import format_results
from searchflights.models import SearchResult


def test_json_output(sample_fares, capsys):
    results = [SearchResult(rank=i + 1, fare=f) for i, f in enumerate(sample_fares[:3])]
    format_results(results, output_format="json", total_legs=10)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 3
    assert data[0]["rank"] == 1
    assert "price" in data[0]


def test_table_output(sample_fares, capsys):
    results = [SearchResult(rank=i + 1, fare=f) for i, f in enumerate(sample_fares[:2])]
    format_results(results, output_format="table", total_legs=5)

    captured = capsys.readouterr()
    assert "BOM" in captured.out
    assert "cheapest option" in captured.out.lower()


def test_empty_results_table(capsys):
    format_results([], output_format="table", total_legs=0)
    captured = capsys.readouterr()
    assert "no results" in captured.out.lower()
