def summarize(records: list) -> dict:
    """Return {"count": int, "total_revenue": float} over enriched records."""
    count = len(records)
    total_revenue = float(sum(r["total"] for r in records))
    return {"count": count, "total_revenue": total_revenue}
