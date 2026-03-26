# Metrics Glossary

Definitions for every financial metric calculated or referenced in this model.
All monetary values are in USD unless noted.

---

## Revenue Metrics

### MRR — Monthly Recurring Revenue
Total subscription revenue recognised in a given calendar month, excluding one-time fees.

```
MRR = Σ (customers_eom × monthly_fee) across all paid tiers
```

### ARR — Annual Recurring Revenue
Annualised snapshot of MRR at the end of a given month.

```
ARR = MRR × 12
```

> ARR is a point-in-time measure, not a trailing 12-month sum.

### Subscription Revenue
Revenue from fixed monthly fees charged to paying customers regardless of usage.

### Overage Revenue
Revenue generated when a customer's API call volume exceeds their tier's
included allocation.

```
Overage Revenue = (Overage Calls / 1,000) × Overage Rate per 1k Calls
```

### Total Revenue
```
Total Revenue = Subscription Revenue + Overage Revenue
```

---

## Customer Metrics

### Customers BOM / EOM
- **BOM** — Beginning of Month: customer count before churn and new adds for that month.
- **EOM** — End of Month: customer count after churn and new adds.

### Paying Customers
Customers on a paid tier (Starter, Growth, or Enterprise). Free-tier users are
excluded from paying-customer counts used in headcount trigger calculations.

### New Customers
Customers added in a given month (gross adds, before churn).

### Churned Customers
Customers lost in a given month.

```
Churned = Customers BOM × Monthly Churn Rate
```

### Conversion Rate (Free → Paid)
Fraction of Free-tier users who upgrade to a paid tier in a given month.

### Upgrade Rate
Fraction of customers who move to a higher pricing tier in a given month.

---

## Cost Metrics

### COGS — Cost of Goods Sold
Direct costs attributable to delivering the API service.

```
COGS = Infrastructure Cost + Support Cost + Payment Processing Cost
```

| Component | Driver |
|-----------|--------|
| Infrastructure Cost | API call volume × cost per 1k calls |
| Support Cost | Customer count × support cost per customer |
| Payment Processing | Revenue × 2.9% + $0.30 per paying customer |

### OpEx — Operating Expenses
Indirect costs required to operate and grow the business.

```
OpEx = Payroll + Fixed Overheads + Variable Overheads (Marketing)
```

---

## Profitability Metrics

### Gross Profit
```
Gross Profit = Total Revenue − COGS
```

### Gross Margin %
```
Gross Margin % = Gross Profit / Total Revenue × 100
```
Target: ≥ 60%

### EBITDA
Earnings before interest, taxes, depreciation, and amortisation — used as a
proxy for operating cash generation/burn in this model.

```
EBITDA = Gross Profit − OpEx
```

### Burn Rate
Monthly cash consumed when EBITDA is negative (i.e., the business is
pre-profitability).

```
Burn Rate = max(0, −EBITDA)
```

### Cumulative Net Cash
Running total of EBITDA across all months, representing the net cash
position relative to the model start date (before any external funding).

```
Cumulative Net Cash (month n) = Σ EBITDA for months 1..n
```

---

## Unit Economics

### CAC — Customer Acquisition Cost
All-in cost to acquire one new paying customer, including marketing spend,
sales commissions, and tooling.

| Tier | CAC |
|------|-----|
| Free | $0 |
| Starter | $120 |
| Growth | $850 |
| Enterprise | $8,500 |

### LTV — Customer Lifetime Value
Expected total gross profit from a customer over their entire relationship
with the business.

```
LTV = (Monthly Fee × Gross Margin per Customer) / Monthly Churn Rate
```

This is the simple "perpetuity" approximation. For more precision, model
cohort-level LTV using the `notebooks/executive_dashboard.ipynb`.

### LTV:CAC Ratio
The primary unit-economics health indicator.

```
LTV:CAC = LTV / CAC
```

| Benchmark | Interpretation |
|-----------|---------------|
| < 1× | Acquiring customers at a loss — unsustainable |
| 1–3× | Borderline — needs improvement |
| ≥ 3× | Healthy — minimum target for this model |
| ≥ 5× | Strong — pricing or cost structure advantage |

### Payback Period
Number of months to recover the CAC through gross profit per customer.

```
Payback Months = CAC / (Monthly Fee − COGS per Customer)
```

Target: ≤ 18 months

### Average Revenue per User (ARPU)
```
ARPU = Total Revenue / Total Active Customers (paid + free)
```

### Net Revenue Retention (NRR)
Revenue from an existing cohort in the current period relative to the same
cohort in the prior period, including expansions (upgrades, overage) and
contractions (downgrades, churn).

> NRR is not directly computed in `compute_metrics.py` but can be derived
> from `simulated_inputs.csv` using cohort analysis in the notebook.

---

## Commonly Confused Terms

| Term A | Term B | Difference |
|--------|--------|-----------|
| MRR | ARR | MRR is monthly; ARR = MRR × 12 (point-in-time annualisation) |
| Gross Margin | Net Margin | Gross margin excludes OpEx; net margin includes all costs |
| Churn Rate | Churn Count | Rate is %; count is absolute number of customers lost |
| LTV | CLTV | The same metric — LTV and CLTV (Customer LTV) are interchangeable |
| CAC | CPA | CAC is specific to paying customers; CPA (Cost per Acquisition) may include free signups |
