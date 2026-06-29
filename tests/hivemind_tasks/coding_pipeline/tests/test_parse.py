"""Leaf oracle for parse — CONTRACT-ENFORCING: asserts exact key names and types."""
from parse import parse


def test_basic_records():
    result = parse("1,apple,3,1.50\n2,banana,0,2.00")
    assert len(result) == 2
    assert result[0] == {"id": 1, "product": "apple", "qty": 3, "price": 1.50}
    assert result[1] == {"id": 2, "product": "banana", "qty": 0, "price": 2.00}


def test_exact_keys():
    """Contract: output dicts must have EXACTLY the keys id, product, qty, price."""
    r = parse("1,apple,3,1.50")[0]
    assert set(r.keys()) == {"id", "product", "qty", "price"}, (
        f"Keys must be exactly {{id, product, qty, price}}; got {set(r.keys())!r}"
    )


def test_types():
    """Contract: id and qty must be int; price must be float."""
    r = parse("1,apple,3,1.50")[0]
    assert isinstance(r["id"], int), f"id must be int; got {type(r['id'])}"
    assert isinstance(r["product"], str), f"product must be str; got {type(r['product'])}"
    assert isinstance(r["qty"], int), f"qty must be int; got {type(r['qty'])}"
    assert isinstance(r["price"], float), f"price must be float; got {type(r['price'])}"
