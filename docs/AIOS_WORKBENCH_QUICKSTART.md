# AIOS Workbench — Quickstart

`aios-workbench` is the Model B surface of AIOS: a **local-first management
plane you run for your own agent project**. You point AIOS at your repo, your
repo emits short recap packets when it does work, and AIOS observes — building
memory, capability observations, and recommendations — without taking your
repo's execution authority.

This is the 5-minute path. Contract: ASC-0181. Architecture: ASC-0174
(authority-routed management plane), ASC-0179 (ingest protocol).

## 0. Prerequisites

- The AIOS control plane (this `myworld/` repo) on your machine.
- Python 3.11+.

## 1. Install the `aios` command (once)

```bash
aios install            # or: python scripts/aios_install.py install
```

This writes a reversible user-space launcher and (optionally) a user-systemd
service. Uninstall any time with `aios uninstall`.

## 2. Register your repo — `aios init`

From inside your agent project's directory:

```bash
cd /path/to/my-agent-project
aios init --repo myproject
```

This:

- registers `myproject` in the workbench registry (`.aios/workbench/registry.json`)
- writes a `.aios-workbench.json` config in your repo

Only registered repos may emit (DNA Invariant 6 — explicit operator
authorization). Your repo keeps full execution authority; `aios init` only
makes it emit-eligible.

## 3. Start the workbench — `aios workbench`

```bash
aios workbench up
```

This starts the local-first ingest server (binds `127.0.0.1` only) and opens
the Control Center. The workbench never exposes a network surface — hosting is
a separate, deliberated decision (Model A / ASC-0180).

## 4. Emit a recap when your project does work — `aios emit-recap`

After a sprint, a feature, a debugging session — anything worth remembering:

```bash
aios emit-recap \
  --repo myproject \
  --sprint MYP-007 \
  --subject "added a retrieval cache for agent memory" \
  --caps python,sqlite,embeddings \
  --evidence "git:abc1234" \
  --files lib/cache.py,lib/memory.py
```

Every emitted packet carries an explicit consent string — AIOS will not ingest
anything without it.

Then absorb it:

```bash
python scripts/aios_ingest_product_recap.py --apply
```

(With the workbench server running, your project can also `POST` packets
directly to `http://127.0.0.1:8787/aios/ingest` — same packet shape.)

## 5. See what AIOS observed — `aios workbench show`

```bash
aios workbench show --repo myproject
```

Or open the Control Center (`http://127.0.0.1:8765/`) — the **Workbench**
band shows, per repo: sprints absorbed and observed capabilities.

Under the hood each recap becomes:

- a **MemoryOS draft** (reviewable; never auto-accepted — DNA Invariant 2)
- a **CapabilityOS observation** (`cap_myproject_*`, with observation counts)

## The loop

```
aios install   →   aios init   →   <do agent work>   →   aios emit-recap
                                                              │
                  aios workbench show   ←   ingest   ←────────┘
```

The longer you run it, the more AIOS knows about your project: what it did,
what capabilities it leans on, what is worth recommending next. That is the
Model B value — a management plane that remembers your agent work, without
ever owning it.

## What the workbench does NOT do

- It does not run or modify your project's code.
- It does not expose a network endpoint (loopback only).
- It does not auto-accept memory — drafts require review.
- It does not host anything — hosting is Model A (`aios-service`), pending
  the ASC-0180 Hive deliberation.
