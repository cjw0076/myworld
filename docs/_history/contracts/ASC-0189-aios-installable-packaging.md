---
contract_id: ASC-0189
slug: aios-installable-packaging
status: closed
goal: Package AIOS so a fresh machine can install it with one command — a curl|sh installer that clones the AIOS repos and puts the `aios` command on PATH, plus an uninstaller.
created: 2026-05-17 12:45 KST
accepted: 2026-05-17 12:45 KST
closed: 2026-05-17 12:55 KST
close_evidence: install.sh ran end-to-end — cloned myworld/hivemind/memoryOS/CapabilityOS into ~/aios, installed the `aios` shim; `aios device-profile` worked via the installed command; re-run was idempotent (updating, not cloning, no failure); uninstall.sh removed the command and kept the data dir. README.md + docs/AIOS_INSTALL.md written. Named exit met.
acceptance_authority: founder directive "AIOS를 npm, sh 같은걸로 패키징해서 배포할 수 있도록" — operator-level packaging, no escalation rule triggered.
origin: AIOS is deployed (cjw0076/myworld + sibling repos public on GitHub) but there is no install path — a new user must clone four repos and wire the CLI by hand. The "1인 1 AIOS" thesis needs a one-command install.
---

# ASC-0189 AIOS Installable Packaging

DNA references: Invariant 6 (operator override — install is opt-in, uninstall
always available), Invariant 7 (privacy — the installer fetches only public
repos, writes nothing private).

## Scope

repos: `myworld`

allowed_files:

- `install.sh` (new — one-command bootstrap)
- `uninstall.sh` (new)
- `docs/AIOS_INSTALL.md` (new)
- `README.md` (new — points at the installer)
- `docs/contracts/ASC-0189-aios-installable-packaging.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`, `.env.*`, provider credentials, `_from_desktop/**`, `dain/**`, `minyoung/**`

## Design

1. **`install.sh`** — POSIX `sh`, runnable as `curl -fsSL .../install.sh | sh`
   or from a clone. Steps, all idempotent:
   - check prerequisites: `git`, `python3` (>= 3.10);
   - clone (or `git pull`) the AIOS repos with remotes — myworld, hivemind,
     memoryOS, CapabilityOS — from `github.com/cjw0076` into `$AIOS_HOME`
     (default `~/aios`); GenesisOS has no public remote yet, so it is noted
     and skipped, not failed on;
   - install an `aios` shim into a bindir (`~/.local/bin`) that execs
     `$AIOS_HOME/myworld/bin/aios` (the existing launcher entry — single
     source of truth);
   - warn if the bindir is not on PATH;
   - print next steps (`aios setup apply`).
2. **`uninstall.sh`** — removes the shim; leaves `$AIOS_HOME` (the user's
   data/repos) untouched unless `--purge` is passed.
3. **No pip package yet** — the scripts cross-import by bare module name and
   assume the repo layout; a clean `pip install` needs a packaging refactor.
   That is a named follow-on, not this contract. The sh installer is the
   supported path.

## Named Exit

Closed when: `install.sh` is idempotent (a second run updates, does not fail),
installs a working `aios` command, and `uninstall.sh` removes it cleanly —
verified.

## Stop Conditions

- A repo clone fails (network/private) → the installer reports which repo and
  continues with the rest; it does not leave a half-state silently.
- The bindir is not writable → the installer reports it and prints the manual
  PATH step instead of failing opaquely.
