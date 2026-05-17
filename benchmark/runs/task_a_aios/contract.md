# BENCH-A — proration off-by-one fix
contract_id: BENCH-A
status: accepted
goal: unused_days() must count the upgrade day itself; 4 failing tests must pass.
scope: benchmark/fixtures/task_a_bugfix/proration.py
done_condition: pytest test_proration.py → 4 passed
DNA: Invariant 1 (decide before acting), Invariant 5 (provenance).
