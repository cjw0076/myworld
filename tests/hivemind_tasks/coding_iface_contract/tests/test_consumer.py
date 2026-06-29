"""Leaf oracle for consumer — identical to coding_iface (already specifies key 'value')."""
from consumer import process


def test_doubles_value():
    assert process({"value": 42}) == 84


def test_zero():
    assert process({"value": 0}) == 0


def test_negative():
    assert process({"value": -5}) == -10
