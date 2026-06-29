def parse(raw: str) -> list:
    """Parse CSV lines into records with keys: id (int), product (str), qty (int), price (float)."""
    records = []
    for line in raw.strip().splitlines():
        parts = line.split(",")
        records.append({
            "id": int(parts[0]),
            "product": str(parts[1]),
            "qty": int(parts[2]),
            "price": float(parts[3]),
        })
    return records
