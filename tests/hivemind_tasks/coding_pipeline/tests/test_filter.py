"""Leaf oracle for filter — CONTRACT-ENFORCING: asserts keep() reads record["qty"]."""
from filter import keep


def test_removes_zero_qty():
    records = [
        {"id": 1, "product": "apple", "qty": 3, "price": 1.50},
        {"id": 2, "product": "banana", "qty": 0, "price": 2.00},
    ]
    result = keep(records)
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_all_zero_returns_empty():
    records = [{"id": 1, "product": "x", "qty": 0, "price": 1.0}]
    assert keep(records) == []


def test_all_positive_kept():
    records = [
        {"id": 1, "product": "a", "qty": 1, "price": 1.0},
        {"id": 2, "product": "b", "qty": 2, "price": 2.0},
    ]
    assert keep(records) == records
