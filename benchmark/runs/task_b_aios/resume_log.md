# Task B — AIOS resume (fresh session, reads BENCH-B contract)
State available: tokenizer.py + BENCH-B contract (part-1 decision recorded).

Provider reasoning:
- Contract states part 1 CLOSED with the whitespace-collapse decision explicit.
- detokenize therefore = `" ".join(tokens)`; tokenize must NOT be touched.
- No guessing, no ambiguity: the prior decision crossed the session boundary.

Outcome: code correct AND design-intent consistency CERTIFIED against contract.
restart_resume_success = success.
human_reprompt_count = 0 (the contract carried the decision).
