# AIOS Release & Deployment

How AIOS ships. Distribution surfaces, the release process, and the gates.

## Distribution surfaces

| Surface | Artifact | Trigger |
|---|---|---|
| **PyPI** (`aios-os`) | wheel + sdist | push tag `vX.Y.Z` → `.github/workflows/publish.yml` (trusted publishing, env `pypi`) |
| **Docker** (`ghcr.io/cjw0076/myworld`) | image | `.github/workflows/docker.yml` |
| **install.sh** | curl one-liner | `curl -fsSL …/install.sh \| sh` — clones repos + `aios` shim + ambient wire + capability scan |
| **AkashicRecord** | Cloudflare Worker | `deploy/akashic-worker` (`wrangler deploy`) — the live public ledger/API |
| **Codespaces** | devcontainer | the README badge |

`tests.yml` runs the suite on push/PR — the gate before any release.

## Release process (cut a version)

1. **Verify green** — full suite passes (`python -m pytest -q`; run at low machine load).
2. **Bump version** — `pyproject.toml` `version` (semver: MINOR for features, PATCH for fixes).
3. **CHANGELOG** — add the themed entry for the new version (see `CHANGELOG.md`).
4. **Commit** — `chore(release): vX.Y.Z` on `main`.
5. **Tag + push** — `git tag vX.Y.Z && git push origin vX.Y.Z`. ⚠️ **This is the
   founder-GO gate**: the tag push triggers `publish.yml` → a *public, immutable*
   PyPI upload (a version can never be re-uploaded). The operator stages everything
   up to here; the founder approves the tag push.
6. **CI publishes** — `publish.yml` builds + uploads to PyPI; `docker.yml` builds the image.
7. **Worker** (if changed) — `cd deploy/akashic-worker && wrangler deploy` (separate;
   not tag-gated).

## Gates

- **Tests green** before bump (no release on red).
- **Founder GO** for the tag push (public PyPI publish is irreversible).
- **Privacy** — the package ships no secrets, raw exports, or private-path data.
- **Provenance** — CHANGELOG cites the work; the tag is the immutable record.

## Current state (2026-06-24)

- Released: `v0.1.0` (tagged).
- **Staged: `v0.2.0`** — version bumped + CHANGELOG written; ~147 commits of work
  (reliability pillars, capability/memory spines, brand/CLI, onboarding, CLS seeds).
  Full suite green (1258 passed). **Awaiting founder GO to push the `v0.2.0` tag.**
