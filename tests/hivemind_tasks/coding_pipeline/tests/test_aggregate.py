"""Leaf oracle for aggregate — CONTRACT-ENFORCING: asserts exact keys "count" and "total_revenue"."""
from aggregate import summarize


def test_count_and_total_revenue():
    records = [
        {"id": 1, "product": "a", "qty": 3, "price": 1.50, "total": 4.50},
        {"id": 3, "product": "c", "qty": 2, "price": 3.00, "total": 6.00},
    ]
    result = summarize(records)
    assert result == {"count": 2, "total_revenue": 10.50}


def test_empty_input():
    result = summarize([])
    assert result == {"count": 0, "total_revenue": 0.0}


def test_exact_keys_and_types():
    """Contract: output must have EXACTLY keys 'count' (int) and 'total_revenue' (float)."""
    records = [{"id": 1, "product": "a", "qty": 1, "price": 1.0, "total": 1.0}]
    result = summarize(records)
    assert set(result.keys()) == {"count", "total_revenue"}, (
        f"Keys must be exactly {{count, total_revenue}}; got {set(result.keys())!r}"
    )
    assert isinstance(result["count"], int), f"count must be int; got {type(result['count'])}"
    assert isinstance(result["total_revenue"], float), (
        f"total_revenue must be float; got {type(result['total_revenue'])}"
    )
