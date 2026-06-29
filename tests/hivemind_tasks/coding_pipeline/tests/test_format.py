"""Leaf oracle for format — CONTRACT-ENFORCING: asserts exact output string format."""
from format import render


def test_basic_render():
    assert render({"count": 2, "total_revenue": 10.50}) == "count=2 revenue=10.50"


def test_zero_values():
    assert render({"count": 0, "total_revenue": 0.0}) == "count=0 revenue=0.00"


def test_decimal_precision():
    """Contract: revenue must always show exactly 2 decimal places."""
    assert render({"count": 1, "total_revenue": 4.50}) == "count=1 revenue=4.50"
