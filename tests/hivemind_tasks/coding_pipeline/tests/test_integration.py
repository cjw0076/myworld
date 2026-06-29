"""Parent oracle — wires all five pipeline stages end-to-end and asserts exact output.

Pipeline: parse -> keep -> enrich -> summarize -> render.
Fails if ANY stage is wrong or any inter-stage interface contract is violated.
"""
from parse import parse
from filter import keep
from transform import enrich
from aggregate import summarize
from format import render


def test_pipeline():
    raw = "1,apple,3,1.50\n2,banana,0,2.00\n3,cherry,2,3.00"
    records = parse(raw)
    records = keep(records)
    records = enrich(records)
    summary = summarize(records)
    result = render(summary)
    assert result == "count=2 revenue=10.50", (
        f"Expected 'count=2 revenue=10.50', got {result!r}. "
        f"After parse: {len(parse(raw))} records. "
        f"After keep: {len(keep(parse(raw)))} records. "
        f"summary={summary!r}"
    )
