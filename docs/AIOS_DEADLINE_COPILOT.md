# AIOS Deadline Copilot — capability reference

A working, hardened **outside-domain value capability**: turns a student's real
deadlines into a verified, personalized, provenance-tracked action plan — entirely
on the local substrate (free, private, no provider lock). The first concrete proof
of the override goal "AIOS creates value OUTSIDE itself," built 2026-06-05.

## Pipeline (6 control-plane scripts)

```
real input → failover-routed local gen → date-verify → GenesisOS critique
          → provenance receipt → per-student memory → value ledger
```

| concern | script |
|---|---|
| orchestration + input adapters + verify + personalization | `scripts/aios_deadline_copilot.py` |
| churn-resilient substrate routing (local-first fallback) | `scripts/aios_substrate_router.py` |
| HTTP delivery surface (POST /plan) | `scripts/aios_copilot_serve.py` |
| value metric over receipts | `scripts/aios_value_ledger.py` |

## Usage

```bash
# from a sample
python scripts/aios_deadline_copilot.py

# from a real LMS/calendar export, for a specific student (personalizes over time)
python scripts/aios_deadline_copilot.py --ical ~/Downloads/deadlines.ics --student kim
python scripts/aios_deadline_copilot.py --csv assignments.csv --student kim   # course,title,due

# as a service any frontend can call (uri app, shortcut, curl)
python scripts/aios_copilot_serve.py --port 8765
#   curl -XPOST :8765/plan -d '{"ical":"<.ics text>","student":"kim"}'

# value signal across all runs
python scripts/aios_value_ledger.py     # outputs, verify-pass rate, substrate mix, churn fallbacks
```

## Properties (each verified + unit-tested)

- **Real input** — `.ics` (VEVENT/VTODO, prefers DUE→DTEND→DTSTART) and CSV, with
  strict date normalization (invalid dates rejected, not silently mis-compared).
- **Resilient** — generation routes across a local model chain and falls back;
  fails fast if the daemon is down. No hard provider dependency (the moat).
- **Verified** — a deterministic date check (LLM plans, CODE verifies) flags any
  work scheduled after a due date / before today / for an unscheduled course.
- **Quality-gated** — GenesisOS prompt-prison critique (best-effort organ).
- **Personalized** — `--student` keeps per-student memory; prior courses feed the
  next plan ("나를 아는 에이전트"). Student ids are path-traversal-sanitized.
- **Auditable** — every run writes a provenance receipt (substrate served, routing
  trail, gates); the ledger aggregates them.

Hardened via heterogeneous review (codex found 5 real bugs incl. a path-traversal;
all fixed). 30 unit tests across the capability.

## What's NOT here (deploy-target / child-repo)

- **uri UI + reminders** — the student-facing surface (the HTTP service is the
  backend enabler).
- **hive scheduling** — recurring daily runs per student (control plane has
  `aios_primitives.py schedule` / `aios_jobs.py`; activating a live cron is a
  founder/ops decision, not an autonomous default).
- **real per-student MemoryOS graph** — receipts are file-based today; promoting
  to MemoryOS-per-student is the next memory-integration step.

See `docs/AIOS_OUTSIDE_VALUE_HANDOFF_2026-06-05.md` for the productionization path
and founder decision points.
