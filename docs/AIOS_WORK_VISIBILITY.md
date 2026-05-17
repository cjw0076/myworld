# AIOS Work Visibility

ASC-0071 adds a read-only work view so operators can see what AIOS is doing
without opening raw runtime files.

```bash
python scripts/aios_work_view.py status
python scripts/aios_work_view.py status --json
python scripts/aios_work_view.py contract ASC-0067 --json
python scripts/aios_work_view.py tail --limit 20
```

The work view summarizes active contracts, blocked dispatches, latest result
packets, changed files, monitor health, and next actions. It does not expose
raw provider stdout/stderr, private transcripts, raw exports, or secrets.
