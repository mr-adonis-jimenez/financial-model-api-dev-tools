# Model Assumptions

This document describes every assumption used in the financial model.
All values are also stored in machine-readable form in
[`data/inputs/assumptions.json`](../data/inputs/assumptions.json).

---

## 1. Projection Horizon

| Parameter | Value | Notes |
|-----------|-------|-------|
| Start month | 2024-01 | Calendar month of Month 1 |
| Projection length | 36 months | 3-year forward view |
| Currency | USD | All monetary values |

---

## 2. Pricing Tiers

The product uses a **usage-based freemium model** with four tiers.

| Tier | Monthly Fee | Included API Calls | Overage Rate (per 1 k calls) |
|------|-------------|-------------------|------------------------------|
| **Free** | $0 | 1,000 | N/A |
| **Starter** | $49 | 50,000 | $0.80 |
| **Growth** | $299 | 500,000 | $0.50 |
| **Enterprise** | $1,499 | 5,000,000 | $0.20 |

Overage revenue accrues when a customer's monthly call volume exceeds their
tier's included allocation. The overage fraction per tier is also
parameterised (see Section 4).

---

## 3. Customer Acquisition

### Initial Customer Base (Month 0)

| Tier | Count |
|------|-------|
| Free | 200 |
| Starter | 40 |
| Growth | 12 |
| Enterprise | 2 |

### Monthly New Customer Adds

New customers are added each month. The base rate grows monthly at the
tier-specific growth rate.

| Tier | Base New Customers/Month | Monthly Growth Rate |
|------|--------------------------|---------------------|
| Free | 80 | 8% |
| Starter | 18 | 10% |
| Growth | 5 | 12% |
| Enterprise | 1 | 8% |

### Customer Acquisition Cost (CAC)

CAC reflects all-in sales & marketing spend to win one new customer.

| Tier | CAC |
|------|-----|
| Free | $0 (organic) |
| Starter | $120 |
| Growth | $850 |
| Enterprise | $8,500 |

---

## 4. Churn & Upgrades

### Monthly Churn Rates

| Tier | Churn Rate |
|------|-----------|
| Free | 15% |
| Starter | 5% |
| Growth | 2.5% |
| Enterprise | 1% |

Churn rates reflect cancellations as a fraction of the beginning-of-month
customer count.

### Conversion & Upgrade Rates

| Event | Rate |
|-------|------|
| Free → Starter conversion | 4% of Free customers/month |
| Starter → Growth upgrade | 2% of Starter customers/month |
| Growth → Enterprise upgrade | 1% of Growth customers/month |

Conversions are computed before churn is applied within each month.

---

## 5. API Usage

### Average Monthly Calls per Customer

| Tier | Avg Calls/Month |
|------|----------------|
| Free | 600 |
| Starter | 35,000 |
| Growth | 320,000 |
| Enterprise | 3,800,000 |

Usage grows at **5% per month** (compounded) as customers deepen their
integration over time.

### Overage Fraction

The fraction of total calls that exceed the included allocation, generating
overage revenue:

| Tier | Overage Fraction |
|------|-----------------|
| Free | 0% |
| Starter | 20% |
| Growth | 25% |
| Enterprise | 30% |

---

## 6. Unit Economics

| Parameter | Value |
|-----------|-------|
| Infrastructure cost | $0.04 per 1,000 API calls |
| Payment processing | 2.9% + $0.30 per transaction |

### Monthly Support Cost per Customer

| Tier | Cost |
|------|------|
| Free | $0.50 |
| Starter | $4.00 |
| Growth | $18.00 |
| Enterprise | $120.00 |

---

## 7. Headcount

### Initial Headcount by Department

| Department | Headcount |
|-----------|-----------|
| Engineering | 4 |
| Sales | 2 |
| Customer Success | 1 |
| Marketing | 1 |
| Operations | 1 |

### Fully-Loaded Annual Cost by Department

| Department | Annual Cost |
|-----------|------------|
| Engineering | $165,000 |
| Sales | $130,000 |
| Customer Success | $95,000 |
| Marketing | $110,000 |
| Operations | $90,000 |

Costs are divided by 12 to produce a monthly payroll expense.

### Hiring Triggers

Headcount scales automatically with paying customer volume:

| Trigger | Ratio |
|---------|-------|
| +1 Engineering | Every 40 paying customers |
| +1 Sales | Every 25 paying customers |
| +1 Customer Success | Every 50 paying customers |

---

## 8. Operating Expenses

### Monthly Fixed Costs

| Item | Monthly Amount |
|------|---------------|
| Hosting (base) | $2,500 |
| Tooling & SaaS | $1,200 |
| Office & misc | $800 |

### Monthly Variable Costs

| Item | Rate |
|------|------|
| Additional hosting | $80 per 1M API calls |
| Marketing spend | 12% of monthly revenue |

---

## 9. Financial Targets (Validation Thresholds)

These targets are used by `validate_model.py` as CI gate checks.

| Metric | Target |
|--------|--------|
| Gross margin floor | ≥ 60% |
| LTV:CAC minimum | ≥ 3.0× |
| Payback period ceiling | ≤ 18 months |
| ARR at Month 12 | ≥ $500,000 |
| ARR at Month 24 | ≥ $2,000,000 |
| ARR at Month 36 | ≥ $6,000,000 |

---

## Sensitivity Notes

The assumptions most likely to materially affect model outputs (in order
of impact) are:

1. **Monthly churn rates** — small changes compound significantly over 36 months
2. **New customer growth rates** — drives top-of-funnel and ARR trajectory
3. **Free-to-paid conversion rate** — affects quality of the self-serve funnel
4. **Enterprise CAC & ACV** — disproportionate effect on LTV:CAC and payback
5. **Infrastructure cost per call** — affects gross margin at scale

Scenario analysis should focus sensitivity runs on these five levers.
