#!/bin/sh
# AIOS uninstaller — removes the `aios` command.
#
#   sh uninstall.sh            remove the command, keep $AIOS_HOME (your data)
#   sh uninstall.sh --purge    also remove $AIOS_HOME (repos + runtime state)
set -eu

AIOS_HOME="${AIOS_HOME:-$HOME/aios}"
AIOS_BIN="${AIOS_BIN:-$HOME/.local/bin}"

say() { printf '\033[1;36m[aios]\033[0m %s\n' "$1"; }

shim="$AIOS_BIN/aios"
if [ -f "$shim" ]; then
  rm -f "$shim"
  say "removed $shim"
else
  say "no aios command found at $shim"
fi

if [ "${1:-}" = "--purge" ]; then
  if [ -d "$AIOS_HOME" ]; then
    rm -rf "$AIOS_HOME"
    say "purged $AIOS_HOME"
  fi
else
  say "kept $AIOS_HOME (repos + runtime state) — pass --purge to remove it"
fi

# the round-controller service, if installed, is left to `aios install` to
# manage — this uninstaller does not touch user-systemd units.
say "uninstalled. (a round-controller service, if installed, was left intact)"
