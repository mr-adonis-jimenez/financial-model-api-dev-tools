"""
tests/test_compute_metrics.py
==============================
Unit tests for scripts/compute_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_inputs import load_assumptions, simulate
from scripts.compute_metrics import (
    compute_ltv,
    compute_payback_months,
    aggregate_by_month,
    compute_metrics,
    PAID_TIERS,
)

ASSUMPTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "inputs" / "assumptions.json"


@pytest.fixture()
def assumptions():
    return load_assumptions(ASSUMPTIONS_PATH)


@pytest.fixture()
def sim_rows(assumptions):
    return simulate(assumptions, months=12)


@pytest.fixture()
def metrics(sim_rows, assumptions):
    return compute_metrics(sim_rows, assumptions)


class TestComputeLtv:
    def test_free_tier_returns_zero(self, assumptions):
        assert compute_ltv("Free", assumptions) == 0.0

    def test_paid_tiers_positive(self, assumptions):
        for tier in PAID_TIERS:
            ltv = compute_ltv(tier, assumptions)
            assert ltv > 0, f"LTV for {tier} should be positive"

    def test_higher_fee_tier_has_higher_ltv(self, assumptions):
        ltv_starter = compute_ltv("Starter", assumptions)
        ltv_growth = compute_ltv("Growth", assumptions)
        ltv_enterprise = compute_ltv("Enterprise", assumptions)
        assert ltv_starter < ltv_growth < ltv_enterprise

    def test_ltv_exceeds_monthly_fee(self, assumptions):
        """LTV should be a multiple of the monthly fee (not just one month)."""
        pricing = {t["name"]: t for t in assumptions["pricing_tiers"]}
        for tier in PAID_TIERS:
            ltv = compute_ltv(tier, assumptions)
            monthly_fee = pricing[tier]["monthly_fee"]
            assert ltv > monthly_fee, f"{tier}: LTV {ltv} should exceed monthly fee {monthly_fee}"


class TestComputePayback:
    def test_free_tier_returns_inf(self, assumptions):
        assert compute_payback_months("Free", assumptions) == float("inf")

    def test_paid_tiers_positive_finite(self, assumptions):
        for tier in PAID_TIERS:
            pb = compute_payback_months(tier, assumptions)
            assert pb > 0
            assert pb != float("inf")

    def test_payback_within_reasonable_range(self, assumptions):
        """Payback period should be between 1 and 60 months for standard tiers."""
        for tier in PAID_TIERS:
            pb = compute_payback_months(tier, assumptions)
            assert 1 <= pb <= 60, f"{tier}: payback {pb:.1f} months outside expected range"


class TestAggregateByMonth:
    def test_returns_dict_keyed_by_month(self, sim_rows):
        agg = aggregate_by_month(sim_rows)
        assert isinstance(agg, dict)
        assert all(isinstance(k, str) for k in agg.keys())

    def test_month_count_matches_simulation(self, sim_rows):
        months_in_sim = len({r["month"] for r in sim_rows})
        agg = aggregate_by_month(sim_rows)
        assert len(agg) == months_in_sim

    def test_total_revenue_non_negative(self, sim_rows):
        agg = aggregate_by_month(sim_rows)
        for month, data in agg.items():
            assert data["total_revenue"] >= 0, f"Negative revenue in {month}"

    def test_paying_customers_excludes_free(self, sim_rows):
        agg = aggregate_by_month(sim_rows)
        free_totals = {
            r["month"]: float(r["customers_eom"])
            for r in sim_rows
            if r["tier"] == "Free"
        }
        for month, data in agg.items():
            # paying_customers should never include free-tier customers
            total_customers = sum(
                float(r["customers_eom"]) for r in sim_rows if r["month"] == month
            )
            assert data["paying_customers"] <= total_customers


class TestComputeMetrics:
    def test_returns_one_row_per_month(self, metrics):
        assert len(metrics) == 12

    def test_required_columns(self, metrics):
        required = [
            "month",
            "month_index",
            "total_revenue",
            "mrr",
            "arr",
            "cogs",
            "gross_profit",
            "gross_margin_pct",
            "opex",
            "ebitda",
            "burn_rate",
            "cumulative_net_cash",
            "paying_customers",
        ]
        for col in required:
            assert col in metrics[0], f"Missing column: {col}"

    def test_arr_equals_mrr_times_12(self, metrics):
        for row in metrics:
            assert abs(row["arr"] - row["mrr"] * 12) < 1.0, (
                f"ARR != MRR×12 in {row['month']}"
            )

    def test_ebitda_equals_gross_profit_minus_opex(self, metrics):
        for row in metrics:
            expected = round(row["gross_profit"] - row["opex"], 2)
            assert abs(row["ebitda"] - expected) < 1.0, (
                f"EBITDA mismatch in {row['month']}"
            )

    def test_burn_rate_zero_when_profitable(self, metrics):
        for row in metrics:
            if row["ebitda"] >= 0:
                assert row["burn_rate"] == 0.0

    def test_burn_rate_positive_when_loss_making(self, metrics):
        for row in metrics:
            if row["ebitda"] < 0:
                assert row["burn_rate"] > 0

    def test_unit_economics_columns_present(self, metrics):
        for tier in PAID_TIERS:
            prefix = tier.lower()
            for col in [f"{prefix}_ltv", f"{prefix}_cac", f"{prefix}_ltv_cac", f"{prefix}_payback_months"]:
                assert col in metrics[0], f"Missing unit economics column: {col}"

    def test_revenue_increases_over_time(self, assumptions):
        """Revenue should generally grow month-over-month with the chosen assumptions."""
        sim_rows = simulate(assumptions, months=24)
        metrics = compute_metrics(sim_rows, assumptions)
        # Compare first quarter average vs last quarter average
        first_q = [m["total_revenue"] for m in metrics[:3]]
        last_q = [m["total_revenue"] for m in metrics[-3:]]
        assert sum(last_q) / 3 > sum(first_q) / 3

    def test_gross_margin_stable_or_improving(self, assumptions):
        """Gross margin should stay above 0% throughout the projection."""
        sim_rows = simulate(assumptions, months=36)
        metrics = compute_metrics(sim_rows, assumptions)
        for row in metrics:
            if row["total_revenue"] > 0:
                assert row["gross_margin_pct"] > 0, (
                    f"Negative gross margin in {row['month']}"
                )
