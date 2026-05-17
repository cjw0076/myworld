# aios.ingest_protocol.v1

Transport protocol for delivering AIOS packets to the control plane.
Defined by ASC-0179.

## Purpose

Decouples *what* is delivered (packet schemas like `aios.product_recap.v1`)
from *how* it is delivered (transport). The same packet flows over either
transport unchanged, so a product repo's emit code does not change when AIOS
moves from local to hosted.

## Two transports

### `file` transport (default, local, dev)

Drop a packet JSON into `.aios/inbox/<repo>/`. This is the original
ASC-0173 transport and remains valid.

### `http` transport (local-first, hosting-ready)

`POST /aios/ingest` to the local ingest server (`scripts/aios_ingest_server.py`).

- **Bind**: `127.0.0.1` only in protocol v1. Network exposure, auth, and TLS
  are explicitly NOT part of this protocol — they belong to the hosting
  decision (ASC-0180 Hive deliberation).
- **Request body**: any AIOS packet object (e.g. an `aios.product_recap.v1`
  packet). The transport does not wrap or re-shape the packet.
- **Response**:

```json
{ "accepted": true, "receipt_id": "rcpt_<hash>", "reason": "ok" }
```

or on rejection:

```json
{ "accepted": false, "receipt_id": null, "reason": "<validation reason>" }
```

## Idempotency

A packet's stable identity is `(<schema>, <repo>, <sprint_id or packet key>)`.
Re-delivering the same packet is a no-op: the server returns the original
`receipt_id`. This makes retry safe over either transport.

## Storage backend

Both transports converge on the same storage: the `http` server writes
accepted packets into `.aios/inbox/<repo>/`, exactly where the `file`
transport puts them. There is one and only one ingestion path downstream
(`scripts/aios_ingest_product_recap.py`). The http server is a transport
adapter, not a second ingestion implementation.

## Authority (DNA alignment)

- DNA Preamble 3: the local operator is the root of trust. A `127.0.0.1`-only
  server does not cross a machine boundary, so it does not change the trust
  model. Hosting (a non-localhost bind) WOULD change it — that is why hosting
  is reserved to ASC-0180.
- DNA Authority Model (ASC-0174): delivery is the `ingest` system call.
  AIOS-owned records produced from ingested packets are pre-fact gated by
  `aios_ingest_product_recap.py` (consent check, privacy markers). The
  transport does not bypass those gates.

## Hosting-ready note

When ASC-0180 decides the hosting question, the only change for a product
repo is the `http` transport base URL: `http://127.0.0.1:<port>` becomes a
hosted origin. The packet schema, the idempotency rule, the response shape,
and the downstream ingestion path are all unchanged. This contract exists so
that switch is configuration, not a rewrite.
