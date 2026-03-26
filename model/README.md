# Financial Model — Excel Workbook

This directory contains the Excel-based financial model for the API SaaS product.

## File

| File | Description |
|------|-------------|
| `API_SaaS_Financial_Model.xlsx` | Master financial model workbook |

> **Note:** The Excel workbook is not tracked in version control by default due to binary
> merge-conflict concerns. Add it to this folder locally. All scalar assumptions are also
> maintained in [`/data/inputs/assumptions.json`](../data/inputs/assumptions.json) so that
> Python scripts can regenerate outputs independently of the workbook.

---

## Workbook Structure

The workbook is organised into the following tabs:

| Tab | Purpose |
|-----|---------|
| **Cover** | Title page, version, date, and author |
| **Assumptions** | All input drivers (pricing, growth rates, churn, costs) |
| **Customer Model** | Monthly customer counts by tier and cohort |
| **Revenue** | Subscription + overage revenue build-up |
| **COGS** | Infrastructure, support, and payment processing costs |
| **Gross Profit** | Revenue minus COGS; gross margin % |
| **Opex** | Headcount plan + variable + fixed operating expenses |
| **P&L** | Summary income statement (EBITDA / Net Income) |
| **Unit Economics** | LTV, CAC, payback period, LTV:CAC by tier |
| **Cash Flow** | Monthly and cumulative cash flow; burn rate; runway |
| **Dashboard** | Executive KPI charts and summary table |

---

## Colour Conventions

| Cell colour | Meaning |
|-------------|---------|
| 🟦 Blue | Hard-coded input — edit only in the **Assumptions** tab |
| ⬜ White | Formula — do **not** edit |
| 🟨 Yellow | Override cell — use sparingly for scenario analysis |

---

## Updating the Model

1. Update scalar inputs in the **Assumptions** tab (or in `data/inputs/assumptions.json` and
   re-run `scripts/export_outputs.py` to sync).
2. Verify that the **Customer Model** tab refreshes correctly (no `#REF!` or `#VALUE!` errors).
3. Save a dated copy under `/model/archive/` before distributing externally.

---

## Version History

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 1.0.0 | 2024-01 | — | Initial model build |
