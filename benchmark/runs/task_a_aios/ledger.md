## BENCH-A — proration off-by-one
- repo: myworld | agent: claude@myworld | role: operator
- changed: benchmark/fixtures/task_a_bugfix/proration.py (unused_days +1)
- evidence: pytest test_proration.py → 4 passed
- status: closed
