"""Leaf oracle for producer — CONTRACT-ENFORCING: asserts the exact key name 'value'.

Unlike coding_iface/tests/test_producer.py which is key-name-agnostic (passes for any
key whose value is 42), this oracle ENFORCES the shared interface contract: the producer
MUST return a dict with key exactly 'value'. A producer returning {'amount': 42} FAILS
this oracle, closing the composition gap at the leaf level.
"""
from producer import get_data


def test_returns_dict():
    result = get_data()
    assert isinstance(result, dict), "get_data() must return a dict"


def test_key_is_value():
    result = get_data()
    assert "value" in result, (
        f"dict must have key 'value' (shared interface contract); got keys: {list(result.keys())!r}"
    )


def test_value_equals_42():
    result = get_data()
    assert result["value"] == 42, (
        f"result['value'] must equal 42; got {result.get('value')!r}"
    )
