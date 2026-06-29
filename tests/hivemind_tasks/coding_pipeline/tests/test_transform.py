"""Leaf oracle for transform — CONTRACT-ENFORCING: asserts "total" key name and value."""
from transform import enrich


def test_adds_total_field():
    records = [{"id": 1, "product": "apple", "qty": 3, "price": 1.50}]
    result = enrich(records)
    assert len(result) == 1
    assert "total" in result[0], (
        f"enrich() must add key 'total' (contract); got keys: {set(result[0].keys())!r}"
    )
    assert result[0]["total"] == 4.50


def test_exact_keys_after_enrich():
    """Contract: enriched dict must have exactly id/product/qty/price/total."""
    records = [{"id": 1, "product": "apple", "qty": 3, "price": 1.50}]
    result = enrich(records)
    assert set(result[0].keys()) == {"id", "product", "qty", "price", "total"}, (
        f"Expected keys {{id, product, qty, price, total}}; got {set(result[0].keys())!r}"
    )


def test_multiple_records():
    records = [
        {"id": 1, "product": "a", "qty": 2, "price": 3.00},
        {"id": 2, "product": "b", "qty": 1, "price": 5.00},
    ]
    result = enrich(records)
    assert result[0]["total"] == 6.00
    assert result[1]["total"] == 5.00
