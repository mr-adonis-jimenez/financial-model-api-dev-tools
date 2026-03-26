"""
tests/test_generate_inputs.py
==============================
Unit tests for scripts/generate_inputs.py
"""

from __future__ import annotations

import json
import csv
from pathlib import Path

import pytest

# Allow importing from scripts/ without installing the package
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_inputs import load_assumptions, simulate, write_csv, TIERS

ASSUMPTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "inputs" / "assumptions.json"


@pytest.fixture()
def assumptions():
    return load_assumptions(ASSUMPTIONS_PATH)


class TestLoadAssumptions:
    def test_loads_successfully(self, assumptions):
        assert isinstance(assumptions, dict)

    def test_required_top_level_keys(self, assumptions):
        required = [
            "model_meta",
            "pricing_tiers",
            "customer_acquisition",
            "churn",
            "api_usage",
            "unit_economics",
            "headcount",
            "operating_expenses",
            "financial_targets",
        ]
        for key in required:
            assert key in assumptions, f"Missing key: {key}"

    def test_pricing_tiers_have_four_tiers(self, assumptions):
        names = [t["name"] for t in assumptions["pricing_tiers"]]
        assert names == TIERS

    def test_financial_targets_present(self, assumptions):
        targets = assumptions["financial_targets"]
        assert "gross_margin_floor" in targets
        assert "ltv_to_cac_floor" in targets
        assert 0 < targets["gross_margin_floor"] < 1


class TestSimulate:
    def test_returns_list(self, assumptions):
        rows = simulate(assumptions, months=3)
        assert isinstance(rows, list)

    def test_row_count_equals_months_times_tiers(self, assumptions):
        months = 6
        rows = simulate(assumptions, months=months)
        assert len(rows) == months * len(TIERS)

    def test_required_columns_present(self, assumptions):
        rows = simulate(assumptions, months=1)
        required_cols = [
            "month",
            "month_index",
            "tier",
            "customers_bom",
            "customers_eom",
            "total_calls",
            "total_revenue",
            "cogs",
            "gross_profit",
            "gross_margin_pct",
        ]
        for col in required_cols:
            assert col in rows[0], f"Missing column: {col}"

    def test_tier_order_per_month(self, assumptions):
        rows = simulate(assumptions, months=1)
        tiers_in_output = [r["tier"] for r in rows]
        assert tiers_in_output == TIERS

    def test_revenue_non_negative(self, assumptions):
        rows = simulate(assumptions, months=12)
        for row in rows:
            assert row["total_revenue"] >= 0, (
                f"Negative revenue in {row['month']} / {row['tier']}"
            )

    def test_free_tier_has_zero_subscription_revenue(self, assumptions):
        rows = simulate(assumptions, months=3)
        free_rows = [r for r in rows if r["tier"] == "Free"]
        for row in free_rows:
            assert row["subscription_revenue"] == 0.0

    def test_gross_profit_equals_revenue_minus_cogs(self, assumptions):
        rows = simulate(assumptions, months=3)
        for row in rows:
            expected = round(row["total_revenue"] - row["cogs"], 2)
            assert abs(row["gross_profit"] - expected) < 0.02, (
                f"Gross profit mismatch in {row['month']} / {row['tier']}"
            )

    def test_month_index_increments(self, assumptions):
        rows = simulate(assumptions, months=4)
        free_rows = [r for r in rows if r["tier"] == "Free"]
        indices = [r["month_index"] for r in free_rows]
        assert indices == list(range(1, 5))

    def test_months_override(self, assumptions):
        for n in (1, 6, 24):
            rows = simulate(assumptions, months=n)
            assert len(rows) == n * len(TIERS)


class TestWriteCsv:
    def test_writes_file(self, tmp_path, assumptions):
        rows = simulate(assumptions, months=2)
        out = tmp_path / "test_output.csv"
        write_csv(rows, out)
        assert out.exists()

    def test_csv_has_correct_row_count(self, tmp_path, assumptions):
        months = 3
        rows = simulate(assumptions, months=months)
        out = tmp_path / "test_output.csv"
        write_csv(rows, out)
        with open(out, newline="", encoding="utf-8") as fh:
            reader = list(csv.DictReader(fh))
        assert len(reader) == months * len(TIERS)

    def test_csv_columns_match_rows(self, tmp_path, assumptions):
        rows = simulate(assumptions, months=1)
        out = tmp_path / "test_output.csv"
        write_csv(rows, out)
        with open(out, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            csv_cols = reader.fieldnames
        assert csv_cols == list(rows[0].keys())

    def test_empty_rows_creates_no_file(self, tmp_path):
        out = tmp_path / "empty.csv"
        write_csv([], out)
        assert not out.exists()
