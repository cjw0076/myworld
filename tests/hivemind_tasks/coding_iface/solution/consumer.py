"""Reference solution: reads key 'value' from the producer dict and doubles it."""


def process(data: dict) -> int:
    return data["value"] * 2
