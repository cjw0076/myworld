# docs/_history — fossil quarantine (kernel audit, executed 2026-06-10)

Prescribed by `docs/AIOS_MINIMUM_KERNEL_AUDIT.md` §Archive (2026-05-20), executed
2026-06-10: internal development history is educational corpus, not a user's
starting state. Files here are MOVED (git mv — content intact, history preserved,
append-only DNA #3 respected), never edited or deleted.

- `contracts/` — 222 terminal contracts (last status ∈ closed / superseded /
  superseded-by-rewrite / withdrawn). The 9 ACTIVE contracts (proposed / accepted /
  deferred / dispatched_next) remain in `docs/contracts/`.
- `sessions/` — operator session logs (formerly `docs/operator_sessions/`).

Rules:

1. **ASC numbers are never reissued.** `aios_contract_autodraft.next_contract_id`
   scans this directory too — quarantine must not cause ID reuse.
2. **Old path references are historical.** Ledger entries / dispatch packets that
   cite `docs/contracts/ASC-NNNN-*` refer to files now under
   `docs/_history/contracts/` with unchanged filenames.
3. When an active contract reaches a terminal status, move it here as part of
   the closeout.
