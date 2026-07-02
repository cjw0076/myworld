Write a Python module defining exactly:
    def ipv4_lenient(s: str) -> bool:
Return True iff s has exactly four dot-separated parts, each a decimal integer 0..255.
IMPORTANT: unlike standard validation, leading zeros ARE allowed here ("01" and "007" are valid).
Reject non-digit parts, empty parts, wrong part count, and values above 255.
Example: ipv4_lenient("01.1.1.1") -> True ; ipv4_lenient("256.1.1.1") -> False.
Output ONLY one fenced python code block.
