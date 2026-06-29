def enrich(records: list) -> list:
    """Add 'total' field (qty * price) to each record; preserve all original keys."""
    result = []
    for r in records:
        enriched = dict(r)
        enriched["total"] = float(r["qty"] * r["price"])
        result.append(enriched)
    return result
