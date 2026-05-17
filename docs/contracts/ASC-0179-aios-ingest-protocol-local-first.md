---
contract_id: ASC-0179
slug: aios-ingest-protocol-local-first
status: closed
goal: Turn the `.aios/inbox` filesystem-drop dispatch boundary into an HTTP-shaped ingest protocol that works local-first (localhost) and is hosting-ready, so both Model A (AIOS as invisible infra under uri) and Model B (AIOS as installable dev product) can serve end users on the same protocol. No hosting commitment — protocol only.
created: 2026-05-15 KST
accepted: 2026-05-15 KST by claude@myworld under delegated authority — local-first protocol work, no DNA trust-model change, no hosting commitment, no founder escalation rule triggered
closed: 2026-05-15 KST — 4/4 stop conditions met: schema doc, loopback-only server, 8/8 tests pass, http-fed packet URI-212 flowed end-to-end
supersedes: none (additive — the filesystem inbox remains a valid transport)
acceptance_authority: founder (serving direction A+B authorized this session); operator-accepted for local-first protocol scope
origin: founder asked "기능들은 다 만들었다면, 어떻게 AIOS를 End user에게 Serving하고 Infra는 어떻게 만들지 고민해봐." Operator analysis: AIOS today is a local single-machine tool; the dispatch substrate is the filesystem (`.aios/inbox`). Both serving models need the filesystem boundary to become a protocol. ASC-0124 verdict says "protocol-core, not infrastructure expansion." This contract does the protocol; ASC-0180 Hive-deliberates the hosting.

---

# ASC-0179 AIOS Ingest Protocol — Local-First

## Why This Exists

ASC-0173 shipped the emit/absorb primitive: a product repo emits an
`aios.product_recap.v1` packet, AIOS ingests it. But the transport is a
file drop into `.aios/inbox/myworld/`. That only works when the product
repo and myworld share a filesystem. uri deploys to Vercel; its production
app cannot drop a file into a local `.aios/inbox`.

The fix is NOT to host AIOS yet (that touches the DNA trust model — see
ASC-0180). The fix is to define the ingest as a **protocol** with two
interchangeable transports:

1. `file` transport — the current `.aios/inbox` drop (local, dev, default)
2. `http` transport — a localhost HTTP endpoint with the same packet shape

Both transports carry the identical packet schema. A product repo emits
the same packet either way. When (and if) AIOS is later hosted, the `http`
transport's base URL changes from `localhost` to a hosted origin — zero
packet-shape change. This is ASC-0124's "protocol-core" principle: the
protocol is stable; the host is a deployment choice made later.

## Scope

repos: `myworld`

allowed_files:

- `docs/schemas/aios_ingest_protocol_v1.md` (new)
- `scripts/aios_ingest_server.py` (new — local-first HTTP ingest server)
- `scripts/aios_ingest_product_recap.py` (extend — accept http-delivered packets)
- `tests/test_aios_ingest_protocol.py` (new)
- `docs/contracts/ASC-0179-aios-ingest-protocol-local-first.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- any deployment manifest (Dockerfile, fly.toml, vercel.json, k8s) — NOT here
- any non-localhost bind — the server binds `127.0.0.1` only in this contract
- any auth/multi-tenant code — single local operator only
- `uri/**` — uri's emit hook already speaks the packet shape (ASC-0173)
- `.env`, `_from_desktop/**`, `dain/**`, `minyoung/**`

## Protocol Definition

`aios.ingest_protocol.v1`:

- **Endpoint**: `POST /aios/ingest` (http transport) OR file drop in
  `.aios/inbox/<repo>/` (file transport)
- **Body**: any existing AIOS packet schema (`aios.product_recap.v1` first;
  `aios.dispatch.v1` and others later) — the protocol is transport, not a
  new packet schema
- **Response** (http): `{ "accepted": bool, "receipt_id": str, "reason": str }`
- **Idempotency**: packets carry a stable id; re-delivery is a no-op with
  the same receipt
- **Authority**: the http server binds `127.0.0.1` only. There is no
  network exposure, no auth, no TLS in this contract. Those belong to the
  hosting decision (ASC-0180). Per DNA Preamble 3, the local operator
  remains the root of trust — a localhost-only server does not change that.

## Work Packets

### Packet A — protocol schema doc

- Write `docs/schemas/aios_ingest_protocol_v1.md`: the two transports, the
  request/response shape, idempotency rule, the explicit localhost-only
  boundary, and a "hosting-ready" note pointing at ASC-0180.

### Packet B — local-first ingest server

- Write `scripts/aios_ingest_server.py`: a stdlib-only
  (`http.server`) HTTP server binding `127.0.0.1:<port>`. `POST /aios/ingest`
  validates the packet, writes it into `.aios/inbox/<repo>/` (reusing the
  file transport as the storage backend), returns a receipt JSON.
- The server is a thin transport adapter — it does NOT re-implement
  ingestion logic. It writes to the same inbox `aios_ingest_product_recap.py`
  already reads. This keeps one ingestion path.

### Packet C — verification test

- `tests/test_aios_ingest_protocol.py`: start the server on an ephemeral
  port, POST a synthetic `aios.product_recap.v1` packet, assert it lands in
  `.aios/inbox/`, assert idempotent re-POST returns the same receipt,
  assert a non-localhost bind is refused.

## Stop Conditions (Named)

Closed when:

1. `docs/schemas/aios_ingest_protocol_v1.md` exists.
2. `scripts/aios_ingest_server.py` runs, binds `127.0.0.1` only, accepts a
   POSTed packet, and writes it to the existing inbox.
3. `tests/test_aios_ingest_protocol.py` passes.
4. A synthetic uri recap packet delivered over http flows end-to-end:
   `POST → inbox → aios_ingest_product_recap.py → memoryOS draft +
   CapabilityOS observation` (the ASC-0173 pipeline, now http-fed).

Fails and escalates to founder if:

- The server binds anything other than `127.0.0.1` (that is the hosting
  decision, reserved to ASC-0180).
- Auth, TLS, or multi-tenant code appears (same reason).
- A second, divergent ingestion path is created instead of reusing the
  ASC-0173 pipeline.

## Relationship to Serving Models

- **Model A** (invisible infra under uri): when AIOS is later hosted, uri's
  emit hook switches its base URL from `localhost` to the hosted origin.
  The packet shape and the ingest pipeline are unchanged. This contract
  makes that switch a one-line config change, not a rewrite.
- **Model B** (installable dev product): a developer who installs AIOS runs
  `aios_ingest_server.py` on their own localhost; their own product repo
  emits to it. No hosting needed — Model B is local-first by nature, and
  this protocol is exactly what it needs.

## Provenance

- founder serving direction: A+B parallel, hosting → Hive (2026-05-15)
- ASC-0124 verdict: protocol-core, not infrastructure expansion
- ASC-0173: the emit/absorb pipeline this protocol fronts
- ASC-0174 DNA Authority Model: ingest is a system call; localhost-only
  server keeps AIOS-owned records pre-fact gated without a trust-model change
- DNA Preamble 3 (operator is root of trust) — unchanged by a localhost server
