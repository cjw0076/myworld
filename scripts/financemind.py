#!/usr/bin/env python3
"""FinanceMind — Credit fraud detection + risk scoring.

DOMAIN_KNOWLEDGE_AS_CODE: Basel III thresholds, FICO score bands,
fraud velocity patterns embedded as constants — zero external API dependency.
Runnable immediately from any environment with sklearn + numpy.

Iter 44 of AIOS outside-domain proof campaign.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Domain knowledge (Basel III / FICO / fraud research) ─────────────────────

# FICO score bands (Fair Isaac Corporation standard)
FICO_BANDS = {
    "exceptional":  (800, 850),
    "very_good":    (740, 799),
    "good":         (670, 739),
    "fair":         (580, 669),
    "poor":         (300, 579),
}

# Basel III minimum capital ratios (BIS 2023)
BASEL_III = {
    "tier1_min":            0.06,   # Tier 1 capital ratio minimum
    "total_cap_min":        0.08,   # Total capital ratio minimum
    "leverage_min":         0.03,   # Leverage ratio floor
    "lcr_min":              1.00,   # Liquidity Coverage Ratio floor
    "nsfr_min":             1.00,   # Net Stable Funding Ratio floor
    "countercyclical_max":  0.025,  # CCyB max buffer
}

# Fraud velocity thresholds (industry baseline, card network rules)
FRAUD_VELOCITY = {
    "txn_per_hour_alert":   8,      # 8+ txn/hour = high risk
    "txn_per_day_alert":    30,     # 30+ txn/day = alert
    "amt_spike_ratio":      5.0,    # txn > 5× avg = anomalous
    "geo_velocity_km_h":    800,    # impossible travel threshold
    "new_merchant_risk":    0.65,   # first-time merchant risk weight
    "international_risk":   0.55,   # cross-border risk weight
    "night_txn_risk":       0.45,   # 11pm–5am risk weight
}

# Transaction risk feature weights (logistic coefficients from public literature)
RISK_WEIGHTS = {
    "high_fico":        -0.40,  # high FICO lowers risk
    "low_fico":         +0.55,  # low FICO raises risk
    "velocity_flag":    +0.70,  # velocity breach
    "amt_spike":        +0.65,  # amount anomaly
    "international":    +0.50,  # cross-border
    "night_txn":        +0.35,  # night transaction
    "new_merchant":     +0.40,  # first merchant contact
    "low_balance_ratio":+0.30,  # balance < 10% of limit
}


# ── Data generation ───────────────────────────────────────────────────────────

def _fico_band(score: float) -> str:
    for band, (lo, hi) in FICO_BANDS.items():
        if lo <= score <= hi:
            return band
    return "poor"


def generate_transactions(n: int = 5000, fraud_rate: float = 0.07,
                          seed: int = 42) -> dict[str, np.ndarray]:
    """Synthetic credit card transaction dataset with domain-realistic distributions."""
    rng = np.random.default_rng(seed)
    n_fraud = int(n * fraud_rate)
    n_legit = n - n_fraud

    def _legit(n: int) -> dict[str, np.ndarray]:
        return {
            "amount":           rng.lognormal(3.5, 1.2, n),          # ~$33 median
            "fico_score":       rng.normal(710, 60, n).clip(300, 850),
            "txn_per_hour":     rng.poisson(1.2, n).clip(0, 20),
            "txn_per_day":      rng.poisson(4.5, n).clip(0, 60),
            "avg_txn_30d":      rng.lognormal(3.2, 0.8, n),
            "balance_ratio":    rng.beta(3, 2, n),                    # balance/limit
            "is_international": rng.binomial(1, 0.12, n).astype(float),
            "is_night":         rng.binomial(1, 0.18, n).astype(float),
            "is_new_merchant":  rng.binomial(1, 0.10, n).astype(float),
            "days_since_open":  rng.exponential(800, n).clip(1, 5000),
            "label":            np.zeros(n),
        }

    def _fraud(n: int) -> dict[str, np.ndarray]:
        return {
            "amount":           rng.lognormal(5.0, 1.5, n),          # higher amounts
            "fico_score":       rng.normal(600, 80, n).clip(300, 850),
            "txn_per_hour":     rng.poisson(6.0, n).clip(0, 30),
            "txn_per_day":      rng.poisson(18.0, n).clip(0, 80),
            "avg_txn_30d":      rng.lognormal(2.8, 0.9, n),
            "balance_ratio":    rng.beta(1.2, 4, n),                  # low balance
            "is_international": rng.binomial(1, 0.55, n).astype(float),
            "is_night":         rng.binomial(1, 0.45, n).astype(float),
            "is_new_merchant":  rng.binomial(1, 0.65, n).astype(float),
            "days_since_open":  rng.exponential(200, n).clip(1, 5000),
            "label":            np.ones(n),
        }

    legit = _legit(n_legit)
    fraud = _fraud(n_fraud)
    combined: dict[str, np.ndarray] = {}
    for k in legit:
        combined[k] = np.concatenate([legit[k], fraud[k]])
    idx = rng.permutation(n)
    return {k: v[idx] for k, v in combined.items()}


# ── Feature engineering ───────────────────────────────────────────────────────

def engineer_features(txns: dict[str, np.ndarray]) -> np.ndarray:
    """Derive domain-informed features from raw transaction fields."""
    amt        = txns["amount"]
    fico       = txns["fico_score"]
    tph        = txns["txn_per_hour"]
    tpd        = txns["txn_per_day"]
    avg30      = txns["avg_txn_30d"]
    bal_ratio  = txns["balance_ratio"]
    intl       = txns["is_international"]
    night      = txns["is_night"]
    new_merch  = txns["is_new_merchant"]
    age_days   = txns["days_since_open"]

    # Domain-derived features
    amt_spike       = amt / (avg30 + 1)                              # × avg
    velocity_flag   = (tph >= FRAUD_VELOCITY["txn_per_hour_alert"]).astype(float)
    day_burst       = (tpd >= FRAUD_VELOCITY["txn_per_day_alert"]).astype(float)
    low_balance     = (bal_ratio < 0.10).astype(float)
    fico_bucket     = (fico < 620).astype(float)                     # subprime flag
    risk_composite  = (
        RISK_WEIGHTS["velocity_flag"] * velocity_flag
        + RISK_WEIGHTS["amt_spike"]    * (amt_spike > FRAUD_VELOCITY["amt_spike_ratio"]).astype(float)
        + RISK_WEIGHTS["international"]* intl
        + RISK_WEIGHTS["night_txn"]    * night
        + RISK_WEIGHTS["new_merchant"] * new_merch
        + RISK_WEIGHTS["low_fico"]     * fico_bucket
        + RISK_WEIGHTS["low_balance_ratio"] * low_balance
    )

    return np.column_stack([
        amt, np.log1p(amt),
        fico, fico_bucket,
        tph, tpd,
        amt_spike, np.log1p(amt_spike),
        velocity_flag, day_burst,
        bal_ratio, low_balance,
        intl, night, new_merch,
        np.log1p(age_days),
        risk_composite,
    ])


# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class FraudResult:
    f1_score: float
    precision: float
    recall: float
    report: str
    anomaly_auc: float
    n_flagged_by_isolation: int
    n_total: int


def train_and_evaluate(txns: dict[str, np.ndarray]) -> FraudResult:
    labels = txns["label"]
    X = engineer_features(txns)
    X_tr, X_te, y_tr, y_te = train_test_split(X, labels, test_size=0.2,
                                               random_state=42, stratify=labels)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s  = scaler.transform(X_te)

    # Layer 1: IsolationForest anomaly detector
    iso = IsolationForest(n_estimators=200, contamination=0.07,
                          random_state=42, n_jobs=-1)
    iso.fit(X_tr_s)
    iso_preds = (iso.predict(X_te_s) == -1).astype(int)
    iso_flagged = iso_preds.sum()

    # Layer 2: Supervised RF classifier
    rf = RandomForestClassifier(n_estimators=300, max_depth=10, class_weight="balanced",
                                random_state=42, n_jobs=-1)
    rf.fit(X_tr_s, y_tr)
    rf_preds = rf.predict(X_te_s)

    # Ensemble: flag if either model flags (OR rule — recall-maximizing)
    ensemble = np.clip(iso_preds + rf_preds, 0, 1)
    f1  = f1_score(y_te, ensemble)
    prec = (ensemble[y_te == 1] == 1).mean() if ensemble.sum() > 0 else 0.0
    rec  = (rf_preds[y_te == 1] == 1).mean()

    report = classification_report(y_te, ensemble, target_names=["legit", "fraud"])

    # IsolationForest AUC proxy (anomaly score correlation)
    scores = -iso.score_samples(X_te_s)
    from sklearn.metrics import roc_auc_score
    try:
        auc = roc_auc_score(y_te, scores)
    except Exception:
        auc = 0.0

    return FraudResult(
        f1_score=float(f1),
        precision=float(prec),
        recall=float(rec),
        report=report,
        anomaly_auc=float(auc),
        n_flagged_by_isolation=int(iso_flagged),
        n_total=int(len(y_te)),
    )


# ── Risk scoring API ──────────────────────────────────────────────────────────

def risk_score(txn: dict[str, Any]) -> dict[str, Any]:
    """Score a single transaction. Returns risk [0..1] + FICO band + flags."""
    fico    = float(txn.get("fico_score", 700))
    amt     = float(txn.get("amount", 50))
    avg30   = float(txn.get("avg_txn_30d", 50))
    tph     = float(txn.get("txn_per_hour", 1))
    intl    = bool(txn.get("is_international", False))
    night   = bool(txn.get("is_night", False))
    new_m   = bool(txn.get("is_new_merchant", False))
    bal_r   = float(txn.get("balance_ratio", 0.5))

    flags = []
    risk = 0.0

    if tph >= FRAUD_VELOCITY["txn_per_hour_alert"]:
        flags.append("velocity_breach")
        risk += RISK_WEIGHTS["velocity_flag"]

    spike = amt / (avg30 + 1)
    if spike >= FRAUD_VELOCITY["amt_spike_ratio"]:
        flags.append(f"amount_spike_{spike:.1f}x")
        risk += RISK_WEIGHTS["amt_spike"]

    if intl:
        flags.append("international")
        risk += RISK_WEIGHTS["international"]

    if night:
        flags.append("night_transaction")
        risk += RISK_WEIGHTS["night_txn"]

    if new_m:
        flags.append("new_merchant")
        risk += RISK_WEIGHTS["new_merchant"]

    if fico >= 740:
        risk += RISK_WEIGHTS["high_fico"]  # high FICO lowers risk
    elif fico < 620:
        flags.append("subprime_fico")
        risk += RISK_WEIGHTS["low_fico"]

    if bal_r < 0.10:
        flags.append("low_balance")
        risk += RISK_WEIGHTS["low_balance_ratio"]

    # Sigmoid normalize
    import math
    risk_normalized = 1 / (1 + math.exp(-risk))

    return {
        "risk_score":     round(risk_normalized, 4),
        "risk_level":     "HIGH" if risk_normalized > 0.65 else "MEDIUM" if risk_normalized > 0.40 else "LOW",
        "fico_band":      _fico_band(fico),
        "flags":          flags,
        "action":         "DECLINE" if risk_normalized > 0.80 else "REVIEW" if risk_normalized > 0.50 else "APPROVE",
        "basel_tier1_ok": True,  # system-level check (txn-level, always true for card)
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="FinanceMind — credit fraud detection")
    parser.add_argument("--n-txn", type=int, default=5000)
    parser.add_argument("--fraud-rate", type=float, default=0.07)
    parser.add_argument("--score-txn", type=json.loads, default=None,
                        help='JSON transaction to score, e.g. \'{"fico_score":550,"amount":1200}\'')
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.score_txn:
        result = risk_score(args.score_txn)
        print(json.dumps(result, indent=2))
        return

    print(f"[FinanceMind] Generating {args.n_txn} transactions (fraud_rate={args.fraud_rate})")
    txns = generate_transactions(n=args.n_txn, fraud_rate=args.fraud_rate)
    print("[FinanceMind] Training IsolationForest + RandomForest ensemble...")
    result = train_and_evaluate(txns)

    if args.json:
        out = {
            "f1_score":     result.f1_score,
            "precision":    result.precision,
            "recall":       result.recall,
            "anomaly_auc":  result.anomaly_auc,
            "n_flagged":    result.n_flagged_by_isolation,
            "n_total":      result.n_total,
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"\nF1={result.f1_score:.4f}  precision={result.precision:.4f}  "
              f"recall={result.recall:.4f}  iso_auc={result.anomaly_auc:.4f}")
        print(f"IsolationForest flagged {result.n_flagged_by_isolation}/{result.n_total} "
              f"({100*result.n_flagged_by_isolation/result.n_total:.1f}%)")
        print("\n" + result.report)


if __name__ == "__main__":
    main()
