"""Leaf oracle for producer — deliberately weak: checks any value equals 42, not the key name."""
from producer import get_data


def test_returns_dict():
    result = get_data()
    assert isinstance(result, dict), "get_data() must return a dict"


def test_has_numeric_42():
    result = get_data()
    assert len(result) > 0, "dict must be non-empty"
    assert any(v == 42 for v in result.values()), (
        f"dict must contain the value 42 (got {result!r})"
    )
