# Task B — BASELINE resume (fresh session, no AIOS record)
State available to the resuming provider: tokenizer.py only.

Provider reasoning (honest reconstruction):
- detokenize is unimplemented. tokenize uses str.split() (no arg).
- AMBIGUITY: split() collapses whitespace runs. Is the lossy round-trip
  intentional, or an unfinished part-1 bug the resumer should fix?
- The code carries no decision. The resuming provider must GUESS.
- A competent provider implements `" ".join(tokens)` — plausibly correct —
  but CANNOT certify it matches prior intent. A provider that values
  round-trip safety may instead "fix" tokenize to preserve whitespace,
  silently contradicting the prior session's deliberate choice.

Outcome: code plausibly correct; design-intent consistency UNVERIFIABLE.
restart_resume_success = partial (state re-derived from code, intent lost).
human_reprompt_count = 1 (founder must re-state the whitespace decision).
