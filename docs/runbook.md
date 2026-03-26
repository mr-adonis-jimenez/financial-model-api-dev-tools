# Runbook — Updating and Running the Financial Model

This runbook explains how to regenerate outputs, update assumptions,
validate the model, and export results for distribution.

---

## Prerequisites

```bash
pip install -r requirements.txt
```

---

## Quick Start (Full Pipeline)

Run the complete pipeline in four commands:

```bash
python scripts/generate_inputs.py
python scripts/compute_metrics.py
python scripts/validate_model.py
python scripts/export_outputs.py
```

All outputs land in `data/outputs/`.

---

## Step 1 — Edit Assumptions

All model inputs live in one file:

```
data/inputs/assumptions.json
```

Open it in any text editor. The file is structured JSON with inline
comments (prefixed with `_comment`). Key sections to update for common
scenarios:

| Scenario | Section(s) to edit |
|----------|--------------------|
| Change pricing | `pricing_tiers[].monthly_fee` / `overage_per_1k_calls` |
| Model a sales push | `customer_acquisition.monthly_new_customers_by_tier` |
| Stress-test churn | `churn.monthly_churn_rate_by_tier` |
| Adjust headcount plan | `headcount.initial_headcount` / `hiring_triggers` |
| Update financial targets | `financial_targets` |

After editing, verify the JSON is valid:

```bash
python -m json.tool data/inputs/assumptions.json > /dev/null && echo "✓ valid JSON"
```

---

## Step 2 — Generate Inputs

```bash
python scripts/generate_inputs.py
```

Optional arguments:

```
--months   N       Override the projection length (default: from assumptions.json)
--out      PATH    Write CSV to a custom location (default: data/outputs/simulated_inputs.csv)
--assumptions PATH Use a different assumptions file
```

Example — run a 12-month scenario:

```bash
python scripts/generate_inputs.py --months 12 --out data/outputs/sim_12m.csv
```

---

## Step 3 — Compute Metrics

```bash
python scripts/compute_metrics.py
```

Optional arguments:

```
--inputs   PATH    Path to simulated_inputs.csv (default: data/outputs/simulated_inputs.csv)
--out      PATH    Write CSV to custom location (default: data/outputs/metrics.csv)
--assumptions PATH Use a different assumptions file
```

---

## Step 4 — Validate

```bash
python scripts/validate_model.py
```

Exit code **0** = all checks pass. Exit code **1** = one or more checks failed.
Failures are printed to stdout with a ✗ prefix.

Optional arguments:

```
--metrics     PATH  Path to metrics.csv (default: data/outputs/metrics.csv)
--assumptions PATH  Use a different assumptions file
```

Checks performed:

1. **Gross margin floor** — must be ≥ threshold in every revenue-generating month.
2. **LTV:CAC floor** — must be ≥ threshold for each paid tier.
3. **Payback period ceiling** — must be ≤ threshold for each paid tier.
4. **ARR milestones** — Month 12, 24, and 36 ARR must meet stated targets.

---

## Step 5 — Export

```bash
python scripts/export_outputs.py
```

Produces:

| File | Description |
|------|-------------|
| `data/outputs/financial_summary.json` | All metrics as JSON (useful for APIs / BI tools) |
| `data/outputs/export_YYYY-MM-DD.xlsx` | Excel workbook with Metrics, Simulated Inputs, and Assumptions sheets |

Optional arguments:

```
--metrics    PATH   Metrics CSV to export
--inputs     PATH   Simulated inputs CSV to export
--out-dir    PATH   Directory for output files
--skip-excel        Skip Excel export (if openpyxl is not installed)
```

---

## Updating the Excel Workbook

1. Open `data/outputs/export_YYYY-MM-DD.xlsx` produced by `export_outputs.py`.
2. Copy the **Metrics** sheet data into the corresponding sheet in
   `model/API_SaaS_Financial_Model.xlsx`.
3. Refresh any pivot tables or chart data sources.
4. Save a dated archive copy under `model/archive/`.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests should pass before any output is distributed externally. The full suite
runs in under a second.

---

## Running in CI (GitHub Actions)

The recommended CI pipeline:

```yaml
- name: Generate and validate financial model
  run: |
    pip install -r requirements.txt
    python scripts/generate_inputs.py
    python scripts/compute_metrics.py
    python scripts/validate_model.py   # exits 1 on failure → blocks merge
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `JSONDecodeError` in `load_assumptions` | Invalid JSON in `assumptions.json` | Run `python -m json.tool data/inputs/assumptions.json` to locate the syntax error |
| Validation fails on gross margin | Infrastructure cost assumptions too high | Reduce `unit_economics.infrastructure_cost_per_1k_calls` or raise prices |
| ARR milestone not reached | Growth rates or new customer adds too low | Increase `customer_acquisition.monthly_new_customers_by_tier` or growth rates |
| `ImportError: No module named openpyxl` | openpyxl not installed | `pip install openpyxl` or pass `--skip-excel` |
| Negative customer counts | Churn rate > 1.0 | Check `churn.monthly_churn_rate_by_tier` values are between 0 and 1 |
