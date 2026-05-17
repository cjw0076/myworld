"""Subscription proration — fixture for benchmark task A (family 1: bug fix).

A customer upgrades mid-cycle. The proration credit for the unused portion of
the old plan should cover the days from the upgrade day (inclusive) to the end
of the billing period (inclusive).
"""

from __future__ import annotations


def unused_days(upgrade_day: int, period_days: int) -> int:
    """Days of the old plan not yet consumed, counting the upgrade day itself.

    upgrade_day is 1-indexed within the period (day 1 .. period_days).
    A customer who upgrades on day 1 has the whole period unused.
    A customer who upgrades on the last day has exactly 1 day unused.
    """
    # BUG: drops the upgrade day itself from the credit.
    return period_days - upgrade_day + 1


def proration_credit(monthly_price: float, upgrade_day: int, period_days: int) -> float:
    """Credit owed back to the customer for the unused portion of the old plan."""
    return round(monthly_price * unused_days(upgrade_day, period_days) / period_days, 2)
