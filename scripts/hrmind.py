#!/usr/bin/env python3
"""HRMind — Employee attrition prediction + retention cost estimation.

DOMAIN_KNOWLEDGE_AS_CODE: SHRM salary benchmarks, engagement score thresholds,
tenure risk curves, manager-span-of-control ratios, and replacement cost
multipliers embedded as constants — no HRIS or ATS API dependency.

Iter 46 of AIOS outside-domain proof campaign.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ── Domain knowledge (SHRM / Gallup / HR analytics research) ─────────────────

# SHRM replacement cost as fraction of annual salary by level
# Source: SHRM 2022 Human Capital Benchmarking Report
REPLACEMENT_COST = {
    "entry":    0.50,   # 50% of annual salary
    "mid":      1.00,   # 100% (recruiting + onboarding + productivity loss)
    "senior":   1.50,   # 150%
    "executive":2.00,   # 200%+
}

# Gallup Q12 engagement → attrition multiplier
# Score 1-5; below 3.0 = "actively disengaged" → 2.6× higher attrition
ENGAGEMENT_RISK = {
    (4.0, 5.0): 0.40,   # highly engaged: 40% of base risk
    (3.0, 4.0): 1.00,   # baseline
    (2.0, 3.0): 1.80,   # disengaged
    (1.0, 2.0): 2.60,   # actively disengaged
}

# Tenure risk curve — attrition peaks at 18 months and 5 years (SHRM data)
TENURE_RISK_MONTHS = {
    (0,  6):   1.20,    # onboarding at-risk
    (6,  18):  1.50,    # peak attrition window
    (18, 36):  1.00,    # stabilization
    (36, 60):  0.80,    # vested loyalty
    (60, 120): 0.70,    # long tenure
    (120, 600):0.90,    # pre-retirement check-in risk
}

# Manager span-of-control: >12 direct reports = engagement/burnout risk
MANAGER_SPAN_RISK_THRESHOLD = 12

# Salary competitiveness (% of market median) → risk multiplier
COMP_RISK = {
    (0.95, 2.0): 0.80,  # above market → retention benefit
    (0.85, 0.95):1.00,  # at market
    (0.75, 0.85):1.40,  # below market
    (0.0,  0.75):1.80,  # significantly below
}

# IBM HR features (open dataset schema — public knowledge)
FEATURE_NAMES = [
    "age", "daily_rate", "distance_from_home", "education",
    "environment_satisfaction", "hourly_rate", "job_involvement",
    "job_level", "job_satisfaction", "monthly_income",
    "monthly_rate", "num_companies_worked", "over_time",
    "percent_salary_hike", "performance_rating",
    "relationship_satisfaction", "stock_option_level",
    "total_working_years", "training_times_last_year",
    "work_life_balance", "years_at_company", "years_in_current_role",
    "years_since_last_promotion", "years_with_curr_manager",
    # domain-engineered features (below)
    "tenure_risk", "comp_risk", "engagement_proxy", "manager_span_risk",
]


# ── Data generation ───────────────────────────────────────────────────────────

def _tenure_risk(months: float) -> float:
    for (lo, hi), risk in TENURE_RISK_MONTHS.items():
        if lo <= months < hi:
            return risk
    return 1.0


def _comp_risk(ratio: float) -> float:
    for (lo, hi), risk in COMP_RISK.items():
        if lo <= ratio < hi:
            return risk
    return 1.0


def generate_employees(n: int = 1500, attrition_rate: float = 0.16,
                       seed: int = 42) -> dict[str, np.ndarray]:
    """Synthetic employee dataset (IBM HR Analytics distribution)."""
    rng = np.random.default_rng(seed)
    n_attr = int(n * attrition_rate)
    n_stay = n - n_attr

    def _cohort(n: int, high_risk: bool) -> dict[str, np.ndarray]:
        age = rng.normal(38 if not high_risk else 32, 9, n).clip(22, 65)
        tenure_months = rng.exponential(36 if not high_risk else 18, n).clip(1, 480)
        monthly_income = rng.lognormal(8.7, 0.5, n).clip(1500, 20000)
        market_median = 5000.0
        comp_ratio = monthly_income / market_median

        return {
            "age":                       age,
            "daily_rate":                rng.integers(100, 1500, n).astype(float),
            "distance_from_home":        rng.integers(1, 30, n).astype(float),
            "education":                 rng.integers(1, 5, n).astype(float),
            "environment_satisfaction":  rng.integers(1, 4, n).astype(float) if not high_risk else rng.integers(1, 3, n).astype(float),
            "hourly_rate":               rng.integers(30, 100, n).astype(float),
            "job_involvement":           rng.integers(1, 4, n).astype(float),
            "job_level":                 rng.integers(1, 5, n).astype(float),
            "job_satisfaction":          rng.integers(1, 4, n).astype(float) if not high_risk else rng.integers(1, 2, n).astype(float),
            "monthly_income":            monthly_income,
            "monthly_rate":              rng.integers(2000, 27000, n).astype(float),
            "num_companies_worked":      rng.integers(0, 9, n).astype(float),
            "over_time":                 (rng.random(n) < (0.28 if high_risk else 0.10)).astype(float),
            "percent_salary_hike":       rng.integers(11, 25, n).astype(float),
            "performance_rating":        rng.integers(3, 4, n).astype(float),
            "relationship_satisfaction": rng.integers(1, 4, n).astype(float),
            "stock_option_level":        rng.integers(0, 3, n).astype(float),
            "total_working_years":       (tenure_months / 12).clip(0, 40),
            "training_times_last_year":  rng.integers(0, 6, n).astype(float),
            "work_life_balance":         rng.integers(1, 4, n).astype(float) if not high_risk else rng.integers(1, 2, n).astype(float),
            "years_at_company":          (tenure_months / 12).clip(0, 40),
            "years_in_current_role":     rng.integers(0, 18, n).astype(float),
            "years_since_last_promotion":rng.integers(0, 15, n).astype(float),
            "years_with_curr_manager":   rng.integers(0, 17, n).astype(float),
            # domain-engineered
            "tenure_risk":               np.array([_tenure_risk(m) for m in tenure_months]),
            "comp_risk":                 np.array([_comp_risk(r) for r in comp_ratio]),
            "engagement_proxy":          (rng.normal(2.8 if high_risk else 3.8, 0.6, n)).clip(1, 5),
            "manager_span_risk":         (rng.integers(3, 20, n) > MANAGER_SPAN_RISK_THRESHOLD).astype(float),
            "label":                     np.ones(n) if high_risk else np.zeros(n),
        }

    stay  = _cohort(n_stay, high_risk=False)
    leave = _cohort(n_attr, high_risk=True)
    merged: dict[str, np.ndarray] = {}
    for k in stay:
        merged[k] = np.concatenate([stay[k], leave[k]])
    idx = rng.permutation(n)
    return {k: v[idx] for k, v in merged.items()}


# ── Model ─────────────────────────────────────────────────────────────────────

@dataclass
class AttritionResult:
    f1_score: float
    roc_auc: float
    report: str
    top_risk_features: list[str]
    predicted_leavers: int
    n_total: int
    estimated_replacement_cost_usd: float


def train_and_evaluate(employees: dict[str, np.ndarray]) -> AttritionResult:
    labels = employees["label"]
    X = np.column_stack([employees[f] for f in FEATURE_NAMES])
    X_tr, X_te, y_tr, y_te = train_test_split(X, labels, test_size=0.2,
                                               random_state=42, stratify=labels)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s  = scaler.transform(X_te)

    # Gradient Boosting — better calibration for HR context
    gb = GradientBoostingClassifier(n_estimators=200, max_depth=4,
                                    learning_rate=0.05, subsample=0.8,
                                    random_state=42)
    gb.fit(X_tr_s, y_tr)
    preds = gb.predict(X_te_s)
    proba = gb.predict_proba(X_te_s)[:, 1]

    f1  = float(f1_score(y_te, preds))
    auc = float(roc_auc_score(y_te, proba))

    # Feature importance via permutation
    pi = permutation_importance(gb, X_te_s, y_te, n_repeats=5, random_state=42)
    feat_ranked = sorted(zip(FEATURE_NAMES, pi.importances_mean),
                         key=lambda x: x[1], reverse=True)
    top_features = [f for f, _ in feat_ranked[:5]]

    # Replacement cost estimate (mid-level avg: $75K/yr → $75K replacement)
    avg_monthly = float(employees["monthly_income"].mean())
    annual_salary = avg_monthly * 12
    n_predicted = int(preds.sum())
    cost = n_predicted * annual_salary * REPLACEMENT_COST["mid"]

    return AttritionResult(
        f1_score=f1,
        roc_auc=auc,
        report=classification_report(y_te, preds, target_names=["stay", "leave"]),
        top_risk_features=top_features,
        predicted_leavers=n_predicted,
        n_total=int(len(y_te)),
        estimated_replacement_cost_usd=round(cost, -2),
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="HRMind — employee attrition prediction")
    parser.add_argument("--n-employees", type=int, default=1500)
    parser.add_argument("--attrition-rate", type=float, default=0.16)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    print(f"[HRMind] {args.n_employees} employees | attrition_rate={args.attrition_rate}", file=sys.stderr)
    employees = generate_employees(n=args.n_employees, attrition_rate=args.attrition_rate)
    print("[HRMind] Training GradientBoosting attrition model...", file=sys.stderr)
    result = train_and_evaluate(employees)

    if args.json:
        out = {
            "f1_score":          result.f1_score,
            "roc_auc":           result.roc_auc,
            "predicted_leavers": result.predicted_leavers,
            "n_total":           result.n_total,
            "top_risk_features": result.top_risk_features,
            "replacement_cost_usd": result.estimated_replacement_cost_usd,
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"\nF1={result.f1_score:.4f}  ROC-AUC={result.roc_auc:.4f}")
        print(f"Predicted leavers: {result.predicted_leavers}/{result.n_total} "
              f"({100*result.predicted_leavers/result.n_total:.1f}%)")
        print(f"Estimated replacement cost: ${result.estimated_replacement_cost_usd:,.0f}")
        print(f"Top risk factors: {', '.join(result.top_risk_features)}")
        print("\n" + result.report)


if __name__ == "__main__":
    main()
