def keep(records: list) -> list:
    """Return only records where qty > 0."""
    return [r for r in records if r["qty"] > 0]
