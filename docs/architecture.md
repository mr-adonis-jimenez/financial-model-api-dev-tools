# Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  API SaaS Financial Model Repository                    │
│                                                                         │
│  ┌──────────────┐   drives   ┌──────────────────────────────────────┐  │
│  │ assumptions  │ ─────────► │       Python Simulation Engine       │  │
│  │    .json     │            │                                      │  │
│  └──────────────┘            │  generate_inputs.py                  │  │
│                              │    ↓ simulated_inputs.csv            │  │
│                              │  compute_metrics.py                  │  │
│                              │    ↓ metrics.csv                     │  │
│                              │  validate_model.py  (CI gate)        │  │
│                              │  export_outputs.py                   │  │
│                              │    ↓ financial_summary.json          │  │
│                              │    ↓ export_YYYY-MM-DD.xlsx          │  │
│                              └──────────────────────────────────────┘  │
│                                            │                            │
│                              ┌─────────────▼──────────────┐            │
│                              │  Excel Workbook (model/)   │            │
│                              │  API_SaaS_Financial_Model  │            │
│                              │  .xlsx                     │            │
│                              └────────────────────────────┘            │
│                                            │                            │
│                              ┌─────────────▼──────────────┐            │
│                              │  Jupyter Dashboard          │            │
│                              │  notebooks/executive_       │            │
│                              │  dashboard.ipynb            │            │
│                              └────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Descriptions

### 1. Assumptions Layer (`data/inputs/assumptions.json`)

The single source of truth for all model inputs. Every number that drives
the simulation originates here. This means the entire model can be re-run
from scratch by editing one file.

Key sections:

| Section | Purpose |
|---------|---------|
| `model_meta` | Projection horizon and start date |
| `pricing_tiers` | Monthly fees, included call volumes, overage rates |
| `customer_acquisition` | Initial counts, monthly new customers, growth rates, CAC |
| `churn` | Monthly churn rates, conversion, and upgrade rates |
| `api_usage` | Average calls per customer, overage fractions, usage growth |
| `unit_economics` | Infrastructure cost per call, support cost, payment processing |
| `headcount` | Department sizes, fully-loaded costs, hiring triggers |
| `operating_expenses` | Fixed and variable overheads |
| `financial_targets` | Validation thresholds (gross margin floor, ARR milestones, etc.) |

---

### 2. Simulation Engine (`scripts/`)

Four scripts that form a linear pipeline:

```
generate_inputs.py  →  compute_metrics.py  →  validate_model.py
                                           →  export_outputs.py
```

| Script | Input | Output |
|--------|-------|--------|
| `generate_inputs.py` | `assumptions.json` | `simulated_inputs.csv` |
| `compute_metrics.py` | `simulated_inputs.csv` + `assumptions.json` | `metrics.csv` |
| `validate_model.py` | `metrics.csv` + `assumptions.json` | Exit 0/1 + console report |
| `export_outputs.py` | `metrics.csv` + `simulated_inputs.csv` | `financial_summary.json` + `.xlsx` |

---

### 3. Excel Workbook (`model/`)

The canonical financial model. See [`model/README.md`](../model/README.md) for tab
descriptions, colour conventions, and version history.

The workbook is intentionally decoupled from the Python layer — it can be
shared as a standalone artefact. The `export_outputs.py` script can
regenerate the data sheets from assumptions alone if the workbook is lost.

---

### 4. Tests (`tests/`)

Pytest suite covering:

- Simulation correctness (revenue signs, gross profit identity)
- Unit economics calculations (LTV, CAC, payback)
- Validation logic (threshold checks pass/fail as expected)

Run with:
```bash
pytest tests/ -v
```

---

### 5. Jupyter Dashboard (`notebooks/`)

Interactive notebook for ad-hoc analysis and presenting results to
stakeholders. Reads from `data/outputs/metrics.csv` so it can be
re-executed after any assumptions change.

---

## Data Flow Summary

```
assumptions.json
      │
      ▼
generate_inputs.py ──► simulated_inputs.csv
      │                       │
      │                       ▼
      └──────────► compute_metrics.py ──► metrics.csv
                                               │
                              ┌────────────────┤
                              │                │
                              ▼                ▼
                    validate_model.py   export_outputs.py
                    (CI gate)           financial_summary.json
                                        export_YYYY-MM-DD.xlsx
```

---

## Design Decisions

1. **JSON over YAML for assumptions** — JSON is natively parseable in both Python and
   JavaScript, has no indentation-sensitivity, and is directly embeddable in REST APIs.

2. **CSV as intermediate format** — simple, portable, and importable into Excel without
   any tooling. Avoids dependency on a database for a model of this scale.

3. **Scripts, not a framework** — each script is a self-contained module with a `main()`
   entry point and can be called from CLI, CI, or imported by tests. This keeps the
   dependency surface minimal.

4. **Validation as a CI gate** — `validate_model.py` exits with code 1 on failure,
   making it suitable as a GitHub Actions step that blocks merges when assumptions
   drift outside acceptable bounds.
