def render(summary: dict) -> str:
    """Render summary as 'count=N revenue=X.XX'."""
    return f"count={summary['count']} revenue={summary['total_revenue']:.2f}"
