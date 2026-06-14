# Installing AIOS

AIOS installs with one command. Contract: ASC-0189.

## Prerequisites

| Requirement | Notes |
|---|---|
| `git` | clones the AIOS repos |
| `python3 >= 3.10` | runs all AIOS scripts |
| **Ollama** (for AI responses) | `curl -fsSL https://ollama.com/install.sh \| sh` |

The installer checks `git` and `python3` for you. Ollama is needed for `aios serve`
and `aios setup apply` (model pulls). If Ollama is absent, setup will warn you and
skip model pulls — everything else still installs.

## Quick install

```sh
curl -fsSL https://raw.githubusercontent.com/cjw0076/myworld/main/install.sh | sh
```

This:

1. checks prerequisites (`git`, `python3` >= 3.10);
2. clones the AIOS repos — myworld, hivemind, memoryOS, CapabilityOS — into
   `$AIOS_HOME` (default `~/aios`);
3. installs an `aios` command into `$AIOS_BIN` (default `~/.local/bin`).

The installer is **idempotent** — re-running it updates the repos and
refreshes the command.

## Configure the install

Set these before running to override the defaults:

| Variable | Default | Meaning |
|---|---|---|
| `AIOS_HOME` | `~/aios` | where the repos are cloned |
| `AIOS_BIN` | `~/.local/bin` | where the `aios` command is installed |
| `AIOS_GH` | `https://github.com/cjw0076` | the GitHub org to clone from |

```sh
AIOS_HOME=/opt/aios curl -fsSL .../install.sh | sh
```

If `$AIOS_BIN` is not on your `PATH`, the installer tells you the line to add
to your shell profile.

## After installing

```sh
aios setup apply        # provision local models + config + the always-on service
aios self-model build   # what AIOS knows about itself
aios device-profile     # what this machine can run
```

`aios setup` is capability-aware — on a workstation-class host it pulls the
recommended models automatically; on a small host it stays minimal.

## Updating

Re-run the installer, or `git pull` inside each repo under `$AIOS_HOME`.

## Uninstalling

```sh
sh "$AIOS_HOME/myworld/uninstall.sh"            # remove the command, keep your data
sh "$AIOS_HOME/myworld/uninstall.sh" --purge    # also remove $AIOS_HOME
```

## Notes

- **GenesisOS** has no public remote yet; the installer notes its absence and
  continues. AIOS runs without it.
- There is no `pip install` package yet — the scripts cross-import by module
  name and assume the repo layout. A packaging refactor for a clean
  `pip`/`pipx` install is a named follow-on; the `sh` installer is the
  supported path.
