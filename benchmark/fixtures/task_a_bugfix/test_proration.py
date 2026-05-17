"""Tests for proration — these are the task's stated done-condition."""

from proration import proration_credit, unused_days


def test_upgrade_on_first_day_credits_whole_period():
    # upgrades day 1 of 30 → whole period unused
    assert unused_days(1, 30) == 30


def test_upgrade_on_last_day_credits_one_day():
    # upgrades on the last day → exactly 1 day unused
    assert unused_days(30, 30) == 1


def test_upgrade_midcycle():
    # upgrades day 10 of 30 → days 10..30 inclusive = 21 days
    assert unused_days(10, 30) == 21


def test_proration_credit_amount():
    # $30/mo, upgrade day 10 of 30 → 21/30 * 30 = $21.00
    assert proration_credit(30.0, 10, 30) == 21.00
