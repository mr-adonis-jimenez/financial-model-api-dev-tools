# financial-model-api-dev-tools

A driver-based financial model designed to simulate revenue, cost structure,
and scalability of an API-based SaaS product.

The Excel workbook in `/model` is the canonical deliverable. This repository
wraps it with a Python simulation engine, validation suite, Jupyter dashboard,
and structured documentation so that every number is traceable,
re-runnable, and CI-gated.

---

## Repository Structure

```
financial-model-api-dev-tools/
├── model/
│   └── README.md                    # Excel workbook guide (tab layout, colour conventions)
│
├── data/
│   ├── inputs/
│   │   └── assumptions.json         # ← single source of truth for all model inputs
│   └── outputs/                     # generated files (git-ignored except .gitkeep)
│
├── scripts/
│   ├── generate_inputs.py           # simulate monthly customer & revenue data
│   ├── compute_metrics.py           # derive P&L, unit economics, and cash flow
│   ├── validate_model.py            # assert financial targets are met (CI gate)
│   └── export_outputs.py            # write JSON + Excel exports
│
├── notebooks/
│   └── executive_dashboard.ipynb    # visualisations for board / exec review
│
├── docs/
│   ├── architecture.md              # system diagram and design decisions
│   ├── assumptions.md               # narrative description of every input
│   ├── metrics_glossary.md          # definitions: MRR, ARR, LTV, CAC, payback, …
│   └── runbook.md                   # step-by-step operating guide
│
├── tests/
│   ├── test_generate_inputs.py
│   ├── test_compute_metrics.py
│   └── test_validate_model.py
│
├── requirements.txt
└── pyproject.toml
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the full pipeline

```bash
python scripts/generate_inputs.py   # → data/outputs/simulated_inputs.csv
python scripts/compute_metrics.py   # → data/outputs/metrics.csv
python scripts/validate_model.py    # exits 0 on pass, 1 on fail
python scripts/export_outputs.py    # → financial_summary.json + export_*.xlsx
```

### 3. Run tests

```bash
pytest tests/ -v
```

### 4. Open the dashboard

```bash
jupyter notebook notebooks/executive_dashboard.ipynb
```

---

## Model Overview

### Pricing Tiers

| Tier | Monthly Fee | Included Calls | Overage |
|------|-------------|----------------|---------|
| Free | $0 | 1,000 | — |
| Starter | $49 | 50,000 | $0.80/1k |
| Growth | $299 | 500,000 | $0.50/1k |
| Enterprise | $1,499 | 5,000,000 | $0.20/1k |

### Key Metrics Computed

- **MRR / ARR** — monthly and annualised recurring revenue
- **Gross Margin** — blended and by tier (target ≥ 60%)
- **EBITDA & Burn Rate** — operating cash generation / consumption
- **LTV, CAC, LTV:CAC** — unit economics per paid tier (target ≥ 3×)
- **Payback Period** — months to recover CAC (target ≤ 18 months)

### Financial Targets (Validation Gates)

| Metric | Target |
|--------|--------|
| Gross margin | ≥ 60% |
| LTV:CAC | ≥ 3.0× |
| Payback period | ≤ 18 months |
| ARR — Month 12 | ≥ $500k |
| ARR — Month 24 | ≥ $2M |
| ARR — Month 36 | ≥ $6M |

---

## Editing Assumptions

All model inputs live in **`data/inputs/assumptions.json`**. Edit that file,
then re-run the pipeline. No code changes required for routine assumption updates.

See [`docs/assumptions.md`](docs/assumptions.md) for a full description of
every parameter.

---

## Documentation

| Document | Contents |
|----------|---------|
| [`docs/architecture.md`](docs/architecture.md) | System diagram, data flow, design decisions |
| [`docs/assumptions.md`](docs/assumptions.md) | Every model input explained |
| [`docs/metrics_glossary.md`](docs/metrics_glossary.md) | Definitions for all financial metrics |
| [`docs/runbook.md`](docs/runbook.md) | Step-by-step operating guide and CI setup |
| [`model/README.md`](model/README.md) | Excel workbook tab guide and colour conventions |

---

## CI Integration

`validate_model.py` returns exit code 1 when any financial target is missed,
making it suitable as a blocking step in a GitHub Actions pipeline:

```yaml
- name: Validate financial model
  run: |
    pip install -r requirements.txt
    python scripts/generate_inputs.py
    python scripts/compute_metrics.py
    python scripts/validate_model.py
```

---

## License

MIT — see [LICENSE](LICENSE).
