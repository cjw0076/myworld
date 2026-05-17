# AIOS Genesis Gate

The Genesis gate is the pre-close challenge surface for AIOS dispatch
releases. It runs GenesisOS divergence tools before a registry contract is
released, then records whether the closeout is free to continue or requires an
operator override.

## Scope

The gate applies to dispatches whose source contract lives under
`docs/contracts/` and has status `accepted` or `closed`.

Synthetic dispatch fixtures, proposed contracts, and explicitly skipped runs
write a `genesis_challenge_skipped` event instead of failing silently.

## Release Behavior

`scripts/aios_dispatch.py release` runs the gate by default for in-registry
accepted or closed contracts.

The challenge report is written to:

```text
.aios/genesis_challenges/<CONTRACT_ID>.json
```

The report includes:

- prompt-prison signatures from the GenesisOS critic
- assumption mutation seed count
- alive branch count
- modality views
- top cross-domain analogies
- `risk_level`
- `soft_block`
- `recommendation`

When `soft_block=true`, release is refused unless the operator passes:

```bash
python scripts/aios_dispatch.py release \
  --dispatch-id <dispatch_id> \
  --operator-override-genesis-block \
  --reason "<operator reason>"
```

To intentionally bypass the gate while preserving provenance:

```bash
python scripts/aios_dispatch.py release \
  --dispatch-id <dispatch_id> \
  --without-genesis-challenge \
  --reason "<operator reason>"
```

## Authority Boundary

GenesisOS is advisory only. The gate may soft-block a release and request
operator review, but it never edits contracts, accepts memory, routes
capabilities, executes work, or selects final truth.

## Ad-Hoc Challenge

Run a challenge without releasing a dispatch:

```bash
python scripts/aios_genesis_challenge.py --contract-id ASC-0050 --json
```

This produces the same report shape under `.aios/genesis_challenges/`.
