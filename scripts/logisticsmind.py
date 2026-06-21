#!/usr/bin/env python3
"""LogisticsMind — Supply chain demand forecasting + inventory optimization.

DOMAIN_KNOWLEDGE_AS_CODE: EOQ formula, safety stock calculations, reorder
point thresholds, ABC classification, and logistics cost constants embedded
as first-class knowledge — no external data feed or ERP dependency.

Iter 45 of AIOS outside-domain proof campaign.
Pattern extension: forecasting + optimization (vs. prior classification work).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.preprocessing import StandardScaler

# ── Domain knowledge (operations research / logistics standards) ──────────────

# EOQ cost parameters (industry typical ranges)
EOQ_PARAMS = {
    "holding_rate":         0.25,    # annual holding cost as fraction of unit cost
    "ordering_cost_usd":    150.0,   # fixed cost per purchase order ($)
    "stockout_penalty":     3.0,     # stockout cost multiplier vs. unit cost
}

# ABC classification thresholds (Pareto principle)
ABC_THRESHOLDS = {
    "A_cumulative_pct":  0.70,   # top 70% of value = A items
    "B_cumulative_pct":  0.90,   # next 20% = B items
    # remaining 10% of value = C items
}

# Service level → z-score (normal distribution quantiles)
SERVICE_LEVELS = {
    0.90: 1.282,
    0.95: 1.645,
    0.98: 2.054,
    0.99: 2.326,
}

# Lead time distribution parameters by supplier tier
LEAD_TIME_DAYS = {
    "tier1_domestic":   {"mean": 3,  "std": 0.5},
    "tier2_regional":   {"mean": 7,  "std": 1.5},
    "tier3_overseas":   {"mean": 21, "std": 5.0},
}

# Seasonality indices by month (retail benchmark, 2023 NRF data)
SEASONALITY_INDEX = {
    1:  0.82,  # Jan (post-holiday dip)
    2:  0.78,
    3:  0.88,
    4:  0.92,
    5:  0.96,
    6:  0.95,
    7:  0.90,
    8:  0.93,
    9:  0.97,
    10: 1.05,
    11: 1.25,  # Nov (pre-holiday surge)
    12: 1.59,  # Dec (holiday peak)
}


# ── Data generation ───────────────────────────────────────────────────────────

def generate_demand_series(
    n_products: int = 20,
    n_weeks: int = 104,   # 2 years
    seed: int = 42,
) -> dict[str, Any]:
    """Synthetic weekly demand series with trend + seasonality + noise."""
    rng = np.random.default_rng(seed)
    weeks = np.arange(n_weeks)
    month_of_week = ((weeks % 52) / 52 * 12).astype(int) % 12 + 1

    products = []
    for i in range(n_products):
        base_demand = rng.uniform(50, 500)
        trend       = rng.uniform(-0.5, 1.5)         # units/week drift
        noise_std   = base_demand * rng.uniform(0.05, 0.20)
        unit_cost   = rng.uniform(5, 200)
        supplier    = rng.choice(list(LEAD_TIME_DAYS.keys()))

        seasonal    = np.array([SEASONALITY_INDEX[m] for m in month_of_week])
        demand      = (base_demand + trend * weeks) * seasonal
        demand      += rng.normal(0, noise_std, n_weeks)
        demand      = np.clip(demand, 0, None)

        products.append({
            "sku":          f"SKU-{i:03d}",
            "demand":       demand,
            "unit_cost":    unit_cost,
            "supplier":     supplier,
            "annual_value": float(demand.mean() * 52 * unit_cost),
        })

    return {"products": products, "n_weeks": n_weeks, "weeks": weeks}


# ── Forecasting ───────────────────────────────────────────────────────────────

def _make_features(demand: np.ndarray, horizon: int = 13) -> tuple[np.ndarray, np.ndarray]:
    """Lag + fourier features for weekly demand forecast."""
    lags = [1, 2, 4, 13, 26, 52]
    max_lag = max(lags)
    X, y = [], []
    n = len(demand)
    for t in range(max_lag, n - horizon):
        feats = [demand[t - lag] for lag in lags]
        # Fourier seasonality (annual cycle)
        week_in_year = t % 52
        feats += [
            math.sin(2 * math.pi * week_in_year / 52),
            math.cos(2 * math.pi * week_in_year / 52),
            math.sin(4 * math.pi * week_in_year / 52),
            math.cos(4 * math.pi * week_in_year / 52),
        ]
        X.append(feats)
        y.append(demand[t + horizon - 1])
    return np.array(X), np.array(y)


def forecast_demand(demand: np.ndarray, horizon: int = 13) -> dict[str, float]:
    """Forecast next `horizon` weeks using Ridge + lag/fourier features."""
    X, y = _make_features(demand, horizon)
    if len(X) < 20:
        return {"mape": float("nan"), "forecast_mean": float(demand[-horizon:].mean())}

    split = int(len(X) * 0.8)
    X_tr, X_te, y_tr, y_te = X[:split], X[split:], y[:split], y[split:]

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s  = scaler.transform(X_te)

    model = Ridge(alpha=1.0)
    model.fit(X_tr_s, y_tr)
    preds = np.clip(model.predict(X_te_s), 0, None)

    mape = mean_absolute_percentage_error(y_te, preds + 1e-6)
    forecast_mean = float(preds[-horizon:].mean()) if len(preds) >= horizon else float(preds.mean())
    return {"mape": float(mape), "forecast_mean": forecast_mean}


# ── Inventory optimization ────────────────────────────────────────────────────

@dataclass
class InventoryPolicy:
    sku: str
    eoq: float            # Economic Order Quantity (units)
    reorder_point: float  # ROP (units)
    safety_stock: float   # safety stock (units)
    annual_cost: float    # total annual inventory cost ($)
    abc_class: str        # A / B / C


def compute_eoq(annual_demand: float, unit_cost: float,
                ordering_cost: float = EOQ_PARAMS["ordering_cost_usd"],
                holding_rate: float = EOQ_PARAMS["holding_rate"]) -> float:
    """Wilson EOQ formula: sqrt(2DS/H)."""
    h = unit_cost * holding_rate
    if h <= 0 or annual_demand <= 0:
        return 1.0
    return math.sqrt(2 * annual_demand * ordering_cost / h)


def compute_safety_stock(demand_std_weekly: float, lead_time_days: float,
                         service_level: float = 0.95) -> float:
    """Safety stock = Z × σ_d × √LT (demand uncertainty during lead time)."""
    z = SERVICE_LEVELS.get(service_level, 1.645)
    lead_time_weeks = lead_time_days / 7
    return z * demand_std_weekly * math.sqrt(lead_time_weeks)


def abc_classify(products: list[dict]) -> dict[str, str]:
    """Classify SKUs by annual value (Pareto ABC)."""
    sorted_p = sorted(products, key=lambda p: p["annual_value"], reverse=True)
    total = sum(p["annual_value"] for p in sorted_p)
    cumulative = 0.0
    classes = {}
    for p in sorted_p:
        cumulative += p["annual_value"] / total
        if cumulative <= ABC_THRESHOLDS["A_cumulative_pct"]:
            classes[p["sku"]] = "A"
        elif cumulative <= ABC_THRESHOLDS["B_cumulative_pct"]:
            classes[p["sku"]] = "B"
        else:
            classes[p["sku"]] = "C"
    return classes


def optimize_inventory(products: list[dict]) -> list[InventoryPolicy]:
    """Compute EOQ + ROP + safety stock for each SKU."""
    abc = abc_classify(products)
    policies = []
    for p in products:
        demand = p["demand"]
        unit_cost = p["unit_cost"]
        supplier  = p["supplier"]
        lt_params = LEAD_TIME_DAYS[supplier]
        lead_time_days = lt_params["mean"] + lt_params["std"]   # conservative

        annual_demand = float(demand.mean() * 52)
        weekly_std    = float(demand.std())

        eoq = compute_eoq(annual_demand, unit_cost)
        safety = compute_safety_stock(weekly_std, lead_time_days)
        avg_demand_lt = demand.mean() * (lead_time_days / 7)
        rop = avg_demand_lt + safety

        # Annual cost: ordering + holding + safety stock holding
        n_orders = annual_demand / max(eoq, 1)
        annual_cost = (
            n_orders * EOQ_PARAMS["ordering_cost_usd"]
            + (eoq / 2 + safety) * unit_cost * EOQ_PARAMS["holding_rate"]
        )

        policies.append(InventoryPolicy(
            sku=p["sku"],
            eoq=round(eoq, 1),
            reorder_point=round(rop, 1),
            safety_stock=round(safety, 1),
            annual_cost=round(annual_cost, 2),
            abc_class=abc[p["sku"]],
        ))
    return policies


# ── Full pipeline ─────────────────────────────────────────────────────────────

@dataclass
class LogisticsResult:
    n_products: int
    n_weeks: int
    avg_mape: float
    best_mape: float
    worst_mape: float
    total_annual_cost: float
    abc_counts: dict[str, int]
    top_eoq_sku: str
    top_eoq_qty: float
    policies_sample: list[dict]


def run_pipeline(n_products: int = 20, n_weeks: int = 104) -> LogisticsResult:
    data = generate_demand_series(n_products=n_products, n_weeks=n_weeks)
    products = data["products"]

    # Forecast
    mapes = []
    for p in products:
        result = forecast_demand(p["demand"], horizon=13)
        p["forecast_mape"] = result["mape"]
        p["forecast_mean"] = result["forecast_mean"]
        if not math.isnan(result["mape"]):
            mapes.append(result["mape"])

    # Inventory optimization
    policies = optimize_inventory(products)

    abc_counts = {"A": 0, "B": 0, "C": 0}
    for pol in policies:
        abc_counts[pol.abc_class] += 1

    top_eoq = max(policies, key=lambda p: p.eoq)
    sample = [asdict(p) for p in sorted(policies, key=lambda p: p.annual_cost, reverse=True)[:5]]

    return LogisticsResult(
        n_products=n_products,
        n_weeks=n_weeks,
        avg_mape=float(np.mean(mapes)) if mapes else float("nan"),
        best_mape=float(np.min(mapes)) if mapes else float("nan"),
        worst_mape=float(np.max(mapes)) if mapes else float("nan"),
        total_annual_cost=sum(p.annual_cost for p in policies),
        abc_counts=abc_counts,
        top_eoq_sku=top_eoq.sku,
        top_eoq_qty=top_eoq.eoq,
        policies_sample=sample,
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="LogisticsMind — supply chain optimization")
    parser.add_argument("--n-products", type=int, default=20)
    parser.add_argument("--n-weeks", type=int, default=104)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    import sys
    print(f"[LogisticsMind] {args.n_products} SKUs × {args.n_weeks} weeks", file=sys.stderr, flush=True)
    result = run_pipeline(n_products=args.n_products, n_weeks=args.n_weeks)

    if args.json:
        out = {
            "avg_mape":          round(result.avg_mape, 4),
            "best_mape":         round(result.best_mape, 4),
            "worst_mape":        round(result.worst_mape, 4),
            "total_annual_cost": round(result.total_annual_cost, 2),
            "abc_counts":        result.abc_counts,
            "top_eoq_sku":       result.top_eoq_sku,
            "top_eoq_qty":       result.top_eoq_qty,
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"Demand forecast  MAPE avg={result.avg_mape:.4f}  "
              f"best={result.best_mape:.4f}  worst={result.worst_mape:.4f}")
        print(f"ABC: A={result.abc_counts['A']} B={result.abc_counts['B']} C={result.abc_counts['C']}")
        print(f"Total annual inventory cost: ${result.total_annual_cost:,.0f}")
        print(f"Highest EOQ: {result.top_eoq_sku} → {result.top_eoq_qty:.0f} units/order")
        print("\nTop-5 cost SKUs:")
        for p in result.policies_sample:
            print(f"  {p['sku']} [{p['abc_class']}] EOQ={p['eoq']:.0f} "
                  f"ROP={p['reorder_point']:.0f} SS={p['safety_stock']:.0f} "
                  f"cost/yr=${p['annual_cost']:,.0f}")


if __name__ == "__main__":
    main()
