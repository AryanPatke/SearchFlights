"""Tests for CLI argument handling."""

from __future__ import annotations

from click.testing import CliRunner

from searchflights import cli


def test_trip_duration_defaults_to_weekish_range(monkeypatch):
    captured = {}

    async def fake_run(query, output_file=None, date_step=None):
        captured["query"] = query

    monkeypatch.setattr(cli, "_run", fake_run)

    result = CliRunner().invoke(
        cli.main,
        ["--origin", "BOM", "--destination", "MLE", "--window", "2026-05-01:2026-05-31"],
    )

    assert result.exit_code == 0
    assert captured["query"].trip_duration_min == 7
    assert captured["query"].trip_duration_max == 10


def test_trip_days_becomes_exact_duration(monkeypatch):
    captured = {}

    async def fake_run(query, output_file=None, date_step=None):
        captured["query"] = query

    monkeypatch.setattr(cli, "_run", fake_run)

    result = CliRunner().invoke(
        cli.main,
        [
            "--origin", "BOM",
            "--destination", "MLE",
            "--window", "2026-05-01:2026-05-31",
            "--trip-days", "4",
        ],
    )

    assert result.exit_code == 0
    assert captured["query"].trip_duration_min == 4
    assert captured["query"].trip_duration_max == 4


def test_trip_days_validates_positive_duration():
    result = CliRunner().invoke(
        cli.main,
        [
            "--origin", "BOM",
            "--destination", "MLE",
            "--window", "2026-05-01:2026-05-31",
            "--trip-days", "0",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--trip-days'" in result.output
