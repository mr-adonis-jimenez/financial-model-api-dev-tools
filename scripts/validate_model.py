"""
validate_model.py
=================
Validates computed financial metrics against the thresholds defined in
data/inputs/assumptions.json under the ``financial_targets`` key.

Checks performed
----------------
1. Gross margin must not fall below ``gross_margin_floor`` in any paying month.
2. LTV:CAC must not fall below ``ltv_to_cac_floor`` for any paid tier.
3. Payback period must not exceed ``payback_period_months_ceiling`` for any paid tier.
4. ARR at month 12, 24, and 36 must meet the stated targets.

Exit codes
----------
0 — all checks passed
1 — one or more checks failed

Usage
-----
    python scripts/validate_model.py \
        [--metrics data/outputs/metrics.csv] \
        [--assumptions data/inputs/assumptions.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ASSUMPTIONS_PATH = ROOT / "data" / "inputs" / "assumptions.json"
DEFAULT_METRICS = ROOT / "data" / "outputs" / "metrics.csv"

PAID_TIERS = ["Starter", "Growth", "Enterprise"]


def load_assumptions(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_metrics(path: Path) -> list[dict[str, Any]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


class ValidationError:
    def __init__(self, check: str, detail: str) -> None:
        self.check = check
        self.detail = detail

    def __str__(self) -> str:
        return f"  ✗ [{self.check}] {self.detail}"


def validate(
    metrics: list[dict[str, Any]],
    assumptions: dict[str, Any],
) -> list[ValidationError]:
    targets = assumptions["financial_targets"]
    acq = assumptions["customer_acquisition"]
    errors: list[ValidationError] = []

    # ── 1. Gross margin floor ─────────────────────────────────────────────────
    gm_floor = targets["gross_margin_floor"] * 100  # convert to %
    for row in metrics:
        if _float(row.get("total_revenue")) <= 0:
            continue
        gm = _float(row.get("gross_margin_pct"))
        if gm < gm_floor:
            errors.append(
                ValidationError(
                    "gross_margin_floor",
                    f"Month {row['month']}: gross margin {gm:.1f}% < floor {gm_floor:.1f}%",
                )
            )

    # ── 2. LTV:CAC floor ─────────────────────────────────────────────────────
    ltv_cac_floor = targets["ltv_to_cac_floor"]
    for tier in PAID_TIERS:
        prefix = tier.lower()
        col = f"{prefix}_ltv_cac"
        if not metrics:
            continue
        # Use the final month value (stable because LTV/CAC are deterministic)
        latest = metrics[-1]
        ratio = _float(latest.get(col))
        if ratio < ltv_cac_floor:
            errors.append(
                ValidationError(
                    "ltv_cac_floor",
                    f"{tier}: LTV:CAC {ratio:.2f} < floor {ltv_cac_floor:.2f}",
                )
            )

    # ── 3. Payback period ceiling ─────────────────────────────────────────────
    payback_ceil = targets["payback_period_months_ceiling"]
    for tier in PAID_TIERS:
        prefix = tier.lower()
        col = f"{prefix}_payback_months"
        if not metrics:
            continue
        latest = metrics[-1]
        pb = _float(latest.get(col))
        if pb == float("inf") or pb > payback_ceil:
            pb_str = "∞" if pb == float("inf") else f"{pb:.1f}"
            errors.append(
                ValidationError(
                    "payback_period_ceiling",
                    f"{tier}: payback {pb_str} months > ceiling {payback_ceil} months",
                )
            )

    # ── 4. ARR milestones ─────────────────────────────────────────────────────
    arr_targets = {
        12: targets["arr_target_month_12"],
        24: targets["arr_target_month_24"],
        36: targets["arr_target_month_36"],
    }
    arr_by_index: dict[int, float] = {
        int(_float(r["month_index"])): _float(r.get("arr")) for r in metrics
    }
    for month_idx, arr_target in arr_targets.items():
        actual = arr_by_index.get(month_idx)
        if actual is None:
            continue  # not enough months simulated — skip
        if actual < arr_target:
            errors.append(
                ValidationError(
                    "arr_milestone",
                    f"Month {month_idx}: ARR ${actual:,.0f} < target ${arr_target:,.0f}",
                )
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate financial model metrics.")
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--assumptions", type=Path, default=ASSUMPTIONS_PATH)
    args = parser.parse_args()

    assumptions = load_assumptions(args.assumptions)
    metrics = read_metrics(args.metrics)

    errors = validate(metrics, assumptions)

    if errors:
        print(f"\n❌  {len(errors)} validation check(s) failed:\n")
        for err in errors:
            print(err)
        print()
        sys.exit(1)
    else:
        print(f"\n✅  All validation checks passed ({len(metrics)} months validated).\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
