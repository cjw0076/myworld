# BENCH-B — tokenizer round-trip, resumed
contract_id: BENCH-B
status: accepted (part 1 closed, part 2 pending)
part_1: tokenize() — CLOSED. Decision recorded: split() with no arg, runs of
        whitespace collapse INTENTIONALLY. Round-trip is lossy BY DESIGN.
part_2: detokenize() — PENDING. Must join tokens with a single space,
        consistent with part 1's recorded decision. Do NOT alter tokenize.
done_condition: detokenize joins single-space; tokenize untouched.
