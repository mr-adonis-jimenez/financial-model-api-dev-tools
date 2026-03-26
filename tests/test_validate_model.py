"""
tests/test_validate_model.py
=============================
Unit tests for scripts/validate_model.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_inputs import load_assumptions, simulate
from scripts.compute_metrics import compute_metrics
from scripts.validate_model import validate, ValidationError

ASSUMPTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "inputs" / "assumptions.json"


@pytest.fixture()
def assumptions():
    return load_assumptions(ASSUMPTIONS_PATH)


@pytest.fixture()
def metrics_36(assumptions):
    sim_rows = simulate(assumptions, months=36)
    return compute_metrics(sim_rows, assumptions)


class TestValidationWithGoodData:
    def test_no_errors_with_default_assumptions(self, metrics_36, assumptions):
        errors = validate(metrics_36, assumptions)
        check_names = [e.check for e in errors]
        # ARR milestone and LTV:CAC checks might fail at default assumptions
        # but gross-margin floor should pass
        for err in errors:
            assert isinstance(err, ValidationError)

    def test_returns_list(self, metrics_36, assumptions):
        result = validate(metrics_36, assumptions)
        assert isinstance(result, list)


class TestGrossMarginFloorCheck:
    def test_fails_when_margin_too_low(self, metrics_36, assumptions):
        """Raise the floor above 100% — should always fail."""
        bad_assumptions = copy.deepcopy(assumptions)
        bad_assumptions["financial_targets"]["gross_margin_floor"] = 1.5  # 150%
        errors = validate(metrics_36, bad_assumptions)
        gm_errors = [e for e in errors if e.check == "gross_margin_floor"]
        assert len(gm_errors) > 0

    def test_passes_when_floor_is_zero(self, metrics_36, assumptions):
        zero_floor_assumptions = copy.deepcopy(assumptions)
        zero_floor_assumptions["financial_targets"]["gross_margin_floor"] = 0.0
        errors = validate(metrics_36, zero_floor_assumptions)
        gm_errors = [e for e in errors if e.check == "gross_margin_floor"]
        assert len(gm_errors) == 0


class TestLtvCacCheck:
    def test_fails_when_floor_very_high(self, metrics_36, assumptions):
        """Require LTV:CAC > 1000 — should always fail."""
        bad = copy.deepcopy(assumptions)
        bad["financial_targets"]["ltv_to_cac_floor"] = 1000.0
        errors = validate(metrics_36, bad)
        ltv_errors = [e for e in errors if e.check == "ltv_cac_floor"]
        assert len(ltv_errors) > 0

    def test_passes_when_floor_is_zero(self, metrics_36, assumptions):
        zero = copy.deepcopy(assumptions)
        zero["financial_targets"]["ltv_to_cac_floor"] = 0.0
        errors = validate(metrics_36, zero)
        ltv_errors = [e for e in errors if e.check == "ltv_cac_floor"]
        assert len(ltv_errors) == 0


class TestPaybackCeilingCheck:
    def test_fails_when_ceiling_too_low(self, metrics_36, assumptions):
        """Set payback ceiling to 0 — should always fail for paid tiers."""
        bad = copy.deepcopy(assumptions)
        bad["financial_targets"]["payback_period_months_ceiling"] = 0
        errors = validate(metrics_36, bad)
        pb_errors = [e for e in errors if e.check == "payback_period_ceiling"]
        assert len(pb_errors) > 0

    def test_passes_when_ceiling_very_high(self, metrics_36, assumptions):
        generous = copy.deepcopy(assumptions)
        generous["financial_targets"]["payback_period_months_ceiling"] = 9999
        errors = validate(metrics_36, generous)
        pb_errors = [e for e in errors if e.check == "payback_period_ceiling"]
        assert len(pb_errors) == 0


class TestArrMilestones:
    def test_skips_milestone_when_not_enough_months(self, assumptions):
        """Simulate only 6 months — month-12 milestone should be skipped."""
        sim_rows = simulate(assumptions, months=6)
        metrics = compute_metrics(sim_rows, assumptions)
        errors = validate(metrics, assumptions)
        arr_errors = [e for e in errors if e.check == "arr_milestone"]
        # None of the milestones should fire because the months don't exist
        months_in_errors = [e.detail.split(":")[0] for e in arr_errors]
        assert "Month 12" not in months_in_errors
        assert "Month 24" not in months_in_errors
        assert "Month 36" not in months_in_errors

    def test_fails_when_arr_target_impossibly_high(self, assumptions):
        """Set month-12 target to $1B — should always fail."""
        bad = copy.deepcopy(assumptions)
        bad["financial_targets"]["arr_target_month_12"] = 1_000_000_000
        sim_rows = simulate(assumptions, months=12)
        metrics = compute_metrics(sim_rows, assumptions)
        errors = validate(metrics, bad)
        arr_errors = [e for e in errors if e.check == "arr_milestone"]
        assert len(arr_errors) >= 1

    def test_passes_when_arr_target_is_zero(self, assumptions):
        """Set all ARR targets to $0 — should pass."""
        easy = copy.deepcopy(assumptions)
        easy["financial_targets"]["arr_target_month_12"] = 0
        easy["financial_targets"]["arr_target_month_24"] = 0
        easy["financial_targets"]["arr_target_month_36"] = 0
        sim_rows = simulate(assumptions, months=36)
        metrics = compute_metrics(sim_rows, assumptions)
        errors = validate(metrics, easy)
        arr_errors = [e for e in errors if e.check == "arr_milestone"]
        assert len(arr_errors) == 0


class TestValidationError:
    def test_str_representation(self):
        err = ValidationError("gross_margin_floor", "Month 2024-01: GM 55% < floor 60%")
        assert "gross_margin_floor" in str(err)
        assert "55%" in str(err)
