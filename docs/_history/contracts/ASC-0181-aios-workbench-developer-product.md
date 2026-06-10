---
contract_id: ASC-0181
slug: aios-workbench-developer-product
status: closed
goal: Consolidate the scattered Model B seeds (native install, Control Center, chat, ingest server) into `aios-workbench` — a coherent local-first developer product where a developer points AIOS at their own agent project, that project emits recap packets, and AIOS observes/absorbs/recommends. Local-first, so no hosting decision (ASC-0180) is needed for Model B.
created: 2026-05-16 KST
accepted: 2026-05-16 KST by claude@myworld — founder GO "B surface 계약 착수"; Model B is local-first (no DNA trust-model change), surface consolidation of already-closed contracts (ASC-0080, ASC-0156)
closed: 2026-05-16 KST — Packet A done (registry-based emit eligibility, aios_emit_recap.py, non-uri repo demoagent flowed end-to-end, unregistered repo rejected, 9/9 tests pass); Packets B-E named
supersedes: none (consolidates; ASC-0080 + ASC-0156 stay closed as seeds)
acceptance_authority: founder GO on "B 먼저, B surface 계약 착수" (2026-05-16)
origin: founder asked how to split Model A (uri infra) and Model B (developer product). Operator analysis: not two products — one substrate, two operator-surfaces. Founder chose "B 먼저, A는 나중". This contract productizes the Model B surface.

---

# ASC-0181 aios-workbench — Developer Product (Model B surface)

## What aios-workbench Is

`aios-workbench` is the Model B surface: a **local-first management plane a
developer runs for their own agent project**. The developer is both the
product-repo operator and the AIOS operator (the two roles that are separate
in Model A collapse into one person here).

It is NOT a new substrate. It is a thin surface over the shared `aios-core`
(5 OS + DNA + ingest protocol + 10 system calls). Model A (`aios-service`,
deferred) will be the same substrate with a hosted surface.

## The Developer Loop

```
aios install              # native install — EXISTS (ASC-0080)
aios init                 # register THIS repo as a product repo — NEW (Packet B)
<dev does agent work in their repo>
aios emit-recap ...       # emit a recap packet — NEW generic tool (Packet A)
aios workbench            # start ingest server + open Control Center — NEW (Packet C)
<Control Center shows what the repo did, what accumulated, what AIOS recommends>
```

The developer sees their own agent project become observable, searchable, and
routed — without surrendering execution authority (per ASC-0174 verdict).

## Inventory — what already exists (seeds)

| Piece | Status | Contract |
|---|---|---|
| native install (`aios install`, user-systemd) | closed | ASC-0080 |
| Control Center web UI (`apps/control/`) | closed | ASC-0156 |
| install-state surfacing in Control Center | closed | ASC-0156 |
| chat surface (`scripts/aios_chat.py`) | exists | — |
| local-first ingest server | closed | ASC-0179 |
| ingest pipeline (recap → memoryOS draft + CapabilityOS obs) | closed | ASC-0173 |
| emit hook | exists but **uri-specific** (`uri/scripts/aios-emit-recap.ts`) | ASC-0173 |

The substrate and most of the surface exist. The gap is **consolidation +
de-uri-fication**: today only `uri` can emit; the workbench needs *any*
registered developer repo to emit.

## Work Packets

### Packet A — generic emit tool + repo registry (THIS CONTRACT implements)

- Owner: `myworld`
- `scripts/aios_ingest_product_recap.py` currently hardcodes
  `ALLOWED_REPOS = {"uri"}`. Replace the hardcode with a **workbench repo
  registry** at `.aios/workbench/registry.json` — a repo is emit-eligible
  iff it is registered.
- Add `scripts/aios_emit_recap.py` — the generic, repo-parameterized
  counterpart of uri's TypeScript hook. Any registered repo emits with
  `--repo <slug>`.
- `aios_ingest_server.py` `KNOWN_REPOS` likewise reads the registry.
- Acceptance: a non-uri repo registered in `registry.json` can emit a
  recap packet that flows end-to-end; an unregistered repo is rejected.

### Packet B — `aios init` (named, follow-on)

- `aios init` in a developer's repo: prompts for a repo slug, writes the
  registry entry, drops a local emit-config. Makes the repo a product repo.

### Packet C — `aios workbench` entry command (named, follow-on)

- One verb that starts the ingest server (ASC-0179) and opens the Control
  Center (`apps/control/`), so the developer has a single entry point
  instead of remembering separate scripts.

### Packet D — Control Center workbench view (named, follow-on)

- A Control Center view showing the developer THEIR product repo's observed
  evidence (sprints absorbed, capabilities observed, memory drafts, AIOS
  recommendations) — in workbench framing, not AIOS-internal contract framing.

### Packet E — quickstart doc (named, follow-on)

- `docs/AIOS_WORKBENCH_QUICKSTART.md` — the developer's 5-minute path:
  install → init → emit → workbench.

## Stop Conditions

Closes when:

1. Packet A done: registry-based emit eligibility; `aios_emit_recap.py`
   exists; a non-uri registered repo flows a recap packet end-to-end;
   unregistered repo rejected.
2. Packets B–E named so they are not lost (drafting each as its own
   contract is the follow-on; naming here satisfies this contract).

Fails / escalates if:

- The workbench forks the substrate (`aios-core` must stay single).
- A hosting / non-localhost surface is added (that is Model A / ASC-0180).
- The emit registry is used to bypass the ASC-0173 consent gate — every
  emitted packet still carries the exact consent string.

## Provenance

- founder GO "B 먼저, B surface 계약 착수" (2026-05-16)
- operator split analysis: one substrate + two operator-surfaces
- seeds: ASC-0080 (native install), ASC-0156 (Control Center), ASC-0173
  (emit/ingest pipeline), ASC-0179 (ingest protocol)
- ASC-0174 Authority Model: workbench is the local operator-surface; the
  developer holds record/schema/participation/override authority for their
  own repo

## Receipts — Packets B–E completed (2026-05-16, founder goal "AIOS 직접완성하자")

Packets B–E were named at close; they are now built and verified:

- **Packet B** — `aios init`: `scripts/aios_workbench_init.py` + launcher verb.
- **Packet C** — `aios workbench`: `scripts/aios_workbench.py` (up/status/stop/show) + launcher verb.
- **Packet D** — Control Center workbench view: `load_workbench()` in `aios_control_snapshot.py`, `renderWorkbench()` + `#workbench-band` in `apps/control/`, `aios workbench show` CLI.
- **Packet E** — `docs/AIOS_WORKBENCH_QUICKSTART.md`.

End-to-end verified on a fresh repo `quickstartdemo` (2026-05-16): aios init → workbench up → http emit → ingest → MemoryOS draft (7 nodes) → workbench show (1 sprint, 2 cap_quickstartdemo_* observations) → stop. Regression: ingest tests OK, CapabilityOS 16 passed.

aios-workbench (Model B surface) is a complete, working, verified developer product.
