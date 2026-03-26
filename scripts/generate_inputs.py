"""
generate_inputs.py
==================
Generates a synthetic month-by-month dataset of API usage and customer
counts driven by the assumptions in data/inputs/assumptions.json.

The output is written to data/outputs/simulated_inputs.csv and can be
used to populate the Excel model or to run the metrics engine
(compute_metrics.py) without the workbook.

Usage
-----
    python scripts/generate_inputs.py [--months 36] [--out data/outputs/simulated_inputs.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ASSUMPTIONS_PATH = ROOT / "data" / "inputs" / "assumptions.json"
DEFAULT_OUTPUT = ROOT / "data" / "outputs" / "simulated_inputs.csv"

TIERS = ["Free", "Starter", "Growth", "Enterprise"]


def load_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _month_label(start: str, offset: int) -> str:
    """Return a YYYY-MM label *offset* months after *start* (format 'YYYY-MM')."""
    year, month = map(int, start.split("-"))
    total_months = year * 12 + (month - 1) + offset
    return f"{total_months // 12:04d}-{(total_months % 12) + 1:02d}"


def simulate(assumptions: dict[str, Any], months: int | None = None) -> list[dict[str, Any]]:
    """Run the simulation and return a list of row dicts (one per tier per month)."""
    meta = assumptions["model_meta"]
    n_months = months if months is not None else meta["projection_months"]
    start = meta["start_month"]

    pricing = {t["name"]: t for t in assumptions["pricing_tiers"]}
    acq = assumptions["customer_acquisition"]
    churn_cfg = assumptions["churn"]
    usage_cfg = assumptions["api_usage"]
    ue = assumptions["unit_economics"]

    customers: dict[str, float] = {
        tier: float(acq["initial_customers_by_tier"][tier]) for tier in TIERS
    }
    new_customers: dict[str, float] = {
        tier: float(acq["monthly_new_customers_by_tier"][tier]) for tier in TIERS
    }

    rows: list[dict[str, Any]] = []

    for m in range(n_months):
        month_label = _month_label(start, m)

        # ── Conversions & upgrades (applied before churn this month) ─────────
        conversions = customers["Free"] * churn_cfg["free_to_paid_conversion_rate"]
        upgrades_s_to_g = customers["Starter"] * churn_cfg["upgrade_rate_starter_to_growth"]
        upgrades_g_to_e = customers["Growth"] * churn_cfg["upgrade_rate_growth_to_enterprise"]

        customers["Free"] -= conversions
        customers["Starter"] += conversions - upgrades_s_to_g
        customers["Growth"] += upgrades_s_to_g - upgrades_g_to_e
        customers["Enterprise"] += upgrades_g_to_e

        for tier in TIERS:
            churn_rate = churn_cfg["monthly_churn_rate_by_tier"][tier]
            churned = customers[tier] * churn_rate

            avg_calls = usage_cfg["avg_calls_per_customer_by_tier"][tier] * (
                (1 + usage_cfg["monthly_usage_growth_rate"]) ** m
            )
            total_calls = max(0.0, customers[tier]) * avg_calls

            tier_cfg = pricing[tier]
            included = tier_cfg["included_calls"]
            overage_rate = tier_cfg["overage_per_1k_calls"]
            overage_frac = usage_cfg["overage_fraction_by_tier"][tier]
            overage_calls = total_calls * overage_frac
            overage_revenue = (overage_calls / 1000) * overage_rate

            subscription_revenue = max(0.0, customers[tier]) * tier_cfg["monthly_fee"]
            total_revenue = subscription_revenue + overage_revenue

            infra_cost = (total_calls / 1000) * ue["infrastructure_cost_per_1k_calls"]
            support_cost = (
                max(0.0, customers[tier]) * ue["support_cost_per_customer_per_month"][tier]
            )
            payment_cost = (
                total_revenue * ue["payment_processing_rate"]
                + (1 if total_revenue > 0 else 0) * ue["payment_processing_fixed"]
            )
            cogs = infra_cost + support_cost + payment_cost
            gross_profit = total_revenue - cogs
            gross_margin = gross_profit / total_revenue if total_revenue > 0 else 0.0

            rows.append(
                {
                    "month": month_label,
                    "month_index": m + 1,
                    "tier": tier,
                    "customers_bom": round(customers[tier] + churned, 2),
                    "new_customers": round(new_customers[tier], 2),
                    "churned_customers": round(churned, 2),
                    "customers_eom": round(customers[tier], 2),
                    "avg_calls_per_customer": round(avg_calls, 0),
                    "total_calls": round(total_calls, 0),
                    "overage_calls": round(overage_calls, 0),
                    "subscription_revenue": round(subscription_revenue, 2),
                    "overage_revenue": round(overage_revenue, 2),
                    "total_revenue": round(total_revenue, 2),
                    "infra_cost": round(infra_cost, 2),
                    "support_cost": round(support_cost, 2),
                    "payment_cost": round(payment_cost, 2),
                    "cogs": round(cogs, 2),
                    "gross_profit": round(gross_profit, 2),
                    "gross_margin_pct": round(gross_margin * 100, 2),
                }
            )

            # ── Apply churn then add new customers for next month ─────────────
            customers[tier] = max(0.0, customers[tier] - churned)
            customers[tier] += new_customers[tier]

        # ── Grow new-customer acquisition ─────────────────────────────────────
        for tier in TIERS:
            growth_rate = acq["monthly_growth_rate_by_tier"][tier]
            new_customers[tier] *= 1 + growth_rate

    return rows


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic API SaaS financial inputs.")
    parser.add_argument("--months", type=int, default=None, help="Override projection months")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output CSV path",
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=ASSUMPTIONS_PATH,
        help="Path to assumptions JSON",
    )
    args = parser.parse_args()

    assumptions = load_assumptions(args.assumptions)
    rows = simulate(assumptions, months=args.months)
    write_csv(rows, args.out)
    print(f"✓ Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
