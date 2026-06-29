"""Parent oracle — identical to coding_iface: wires producer -> consumer end-to-end."""
from producer import get_data
from consumer import process


def test_pipeline():
    data = get_data()
    result = process(data)
    assert result == 84, (
        f"Expected 84, got {result!r}. "
        f"producer returned {data!r}; consumer expects key 'value'."
    )
