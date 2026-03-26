"""
compute_metrics.py
==================
Computes period-level and cumulative unit-economics metrics from the
simulated inputs CSV produced by generate_inputs.py.

Key outputs (written to data/outputs/metrics.csv):
  - Monthly MRR, ARR, and total revenue
  - Blended and per-tier gross margin
  - CAC, LTV, payback period, and LTV:CAC ratio by tier
  - Monthly burn rate and cumulative net cash position

Usage
-----
    python scripts/compute_metrics.py \
        [--inputs  data/outputs/simulated_inputs.csv] \
        [--out     data/outputs/metrics.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ASSUMPTIONS_PATH = ROOT / "data" / "inputs" / "assumptions.json"
DEFAULT_INPUTS = ROOT / "data" / "outputs" / "simulated_inputs.csv"
DEFAULT_OUTPUT = ROOT / "data" / "outputs" / "metrics.csv"

TIERS = ["Free", "Starter", "Growth", "Enterprise"]
PAID_TIERS = ["Starter", "Growth", "Enterprise"]


def load_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_simulated_inputs(path: Path) -> list[dict[str, Any]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def compute_opex(
    month_index: int,
    paying_customers: float,
    total_revenue: float,
    assumptions: dict[str, Any],
) -> float:
    """Estimate total operating expenses for a given month."""
    hc = assumptions["headcount"]
    opex_cfg = assumptions["operating_expenses"]

    # Headcount
    eng_hires = max(0, paying_customers / hc["hiring_triggers"]["engineering_per_n_paying_customers"])
    sales_hires = max(0, paying_customers / hc["hiring_triggers"]["sales_per_n_paying_customers"])
    cs_hires = max(0, paying_customers / hc["hiring_triggers"]["customer_success_per_n_paying_customers"])

    total_eng = max(hc["initial_headcount"]["engineering"], round(eng_hires))
    total_sales = max(hc["initial_headcount"]["sales"], round(sales_hires))
    total_cs = max(hc["initial_headcount"]["customer_success"], round(cs_hires))
    total_mktg = hc["initial_headcount"]["marketing"]
    total_ops = hc["initial_headcount"]["operations"]

    costs = hc["avg_fully_loaded_cost_by_dept"]
    monthly_payroll = (
        total_eng * costs["engineering"]
        + total_sales * costs["sales"]
        + total_cs * costs["customer_success"]
        + total_mktg * costs["marketing"]
        + total_ops * costs["operations"]
    ) / 12

    # Fixed overheads
    fixed = sum(opex_cfg["monthly_fixed"].values())

    # Variable — marketing as % of revenue
    variable = total_revenue * opex_cfg["monthly_variable"]["marketing_spend_pct_of_revenue"]

    return monthly_payroll + fixed + variable


def compute_ltv(tier: str, assumptions: dict[str, Any]) -> float:
    """LTV = (Monthly Revenue per customer × Gross Margin) / Monthly Churn Rate."""
    pricing = {t["name"]: t for t in assumptions["pricing_tiers"]}
    churn_cfg = assumptions["churn"]
    ue = assumptions["unit_economics"]

    monthly_fee = pricing[tier]["monthly_fee"]
    churn_rate = churn_cfg["monthly_churn_rate_by_tier"][tier]
    if churn_rate == 0 or monthly_fee == 0:
        return 0.0

    support_cost = ue["support_cost_per_customer_per_month"][tier]
    payment_cost = monthly_fee * ue["payment_processing_rate"] + ue["payment_processing_fixed"]
    gross_per_customer = monthly_fee - support_cost - payment_cost
    gross_margin_per_customer = gross_per_customer / monthly_fee if monthly_fee > 0 else 0.0

    return (monthly_fee * gross_margin_per_customer) / churn_rate


def compute_payback_months(tier: str, assumptions: dict[str, Any]) -> float:
    """Payback = CAC / (Monthly Revenue × Gross Margin)."""
    pricing = {t["name"]: t for t in assumptions["pricing_tiers"]}
    acq = assumptions["customer_acquisition"]
    ue = assumptions["unit_economics"]

    cac = acq["cac_by_tier"][tier]
    monthly_fee = pricing[tier]["monthly_fee"]
    if monthly_fee == 0:
        return float("inf")

    support_cost = ue["support_cost_per_customer_per_month"][tier]
    payment_cost = monthly_fee * ue["payment_processing_rate"] + ue["payment_processing_fixed"]
    gross_per_customer = monthly_fee - support_cost - payment_cost
    if gross_per_customer <= 0:
        return float("inf")

    return cac / gross_per_customer


def aggregate_by_month(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Pivot the per-tier rows into a dict keyed by month label."""
    by_month: dict[str, dict[str, float]] = {}
    for row in rows:
        m = row["month"]
        if m not in by_month:
            by_month[m] = {
                "month_index": _float(row["month_index"]),
                "total_revenue": 0.0,
                "subscription_revenue": 0.0,
                "overage_revenue": 0.0,
                "cogs": 0.0,
                "gross_profit": 0.0,
                "paying_customers": 0.0,
                "total_calls": 0.0,
            }
        agg = by_month[m]
        agg["total_revenue"] += _float(row["total_revenue"])
        agg["subscription_revenue"] += _float(row["subscription_revenue"])
        agg["overage_revenue"] += _float(row["overage_revenue"])
        agg["cogs"] += _float(row["cogs"])
        agg["gross_profit"] += _float(row["gross_profit"])
        agg["total_calls"] += _float(row["total_calls"])
        if row["tier"] != "Free":
            agg["paying_customers"] += _float(row["customers_eom"])
    return by_month


def compute_metrics(
    simulated_rows: list[dict[str, Any]],
    assumptions: dict[str, Any],
) -> list[dict[str, Any]]:
    by_month = aggregate_by_month(simulated_rows)

    # Pre-compute stable per-tier unit economics
    unit_econ: dict[str, dict[str, float]] = {}
    for tier in TIERS:
        ltv = compute_ltv(tier, assumptions)
        cac = assumptions["customer_acquisition"]["cac_by_tier"][tier]
        payback = compute_payback_months(tier, assumptions)
        unit_econ[tier] = {
            "ltv": ltv,
            "cac": cac,
            "ltv_cac_ratio": ltv / cac if cac > 0 else float("inf"),
            "payback_months": payback,
        }

    cumulative_cash = 0.0
    metrics_rows: list[dict[str, Any]] = []

    for month_label, agg in sorted(by_month.items(), key=lambda x: x[0]):
        idx = int(agg["month_index"])
        total_rev = agg["total_revenue"]
        cogs = agg["cogs"]
        gross_profit = agg["gross_profit"]
        gross_margin = gross_profit / total_rev if total_rev > 0 else 0.0
        mrr = total_rev  # already monthly
        arr = mrr * 12
        paying = agg["paying_customers"]

        opex = compute_opex(idx, paying, total_rev, assumptions)
        ebitda = gross_profit - opex
        burn_rate = -ebitda if ebitda < 0 else 0.0
        cumulative_cash += ebitda

        row: dict[str, Any] = {
            "month": month_label,
            "month_index": idx,
            "total_revenue": round(total_rev, 2),
            "subscription_revenue": round(agg["subscription_revenue"], 2),
            "overage_revenue": round(agg["overage_revenue"], 2),
            "mrr": round(mrr, 2),
            "arr": round(arr, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round(gross_margin * 100, 2),
            "opex": round(opex, 2),
            "ebitda": round(ebitda, 2),
            "burn_rate": round(burn_rate, 2),
            "cumulative_net_cash": round(cumulative_cash, 2),
            "paying_customers": round(paying, 0),
            "total_calls": round(agg["total_calls"], 0),
        }

        # Attach blended unit economics (weighted by paying customers per tier this month)
        for tier in TIERS:
            if tier == "Free":
                continue
            prefix = tier.lower()
            row[f"{prefix}_ltv"] = round(unit_econ[tier]["ltv"], 2)
            row[f"{prefix}_cac"] = round(unit_econ[tier]["cac"], 2)
            row[f"{prefix}_ltv_cac"] = round(unit_econ[tier]["ltv_cac_ratio"], 2)
            row[f"{prefix}_payback_months"] = round(unit_econ[tier]["payback_months"], 2)

        metrics_rows.append(row)

    return metrics_rows


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
    parser = argparse.ArgumentParser(description="Compute unit-economics metrics from simulation.")
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--assumptions", type=Path, default=ASSUMPTIONS_PATH)
    args = parser.parse_args()

    assumptions = load_assumptions(args.assumptions)
    sim_rows = read_simulated_inputs(args.inputs)
    metrics = compute_metrics(sim_rows, assumptions)
    write_csv(metrics, args.out)
    print(f"✓ Wrote {len(metrics)} metric rows to {args.out}")


if __name__ == "__main__":
    main()
