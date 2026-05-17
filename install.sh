#!/bin/sh
# AIOS installer — one-command bootstrap of a personal AIOS (1인 1 AIOS).
#
#   curl -fsSL https://raw.githubusercontent.com/cjw0076/myworld/main/install.sh | sh
#
# Idempotent: a second run updates the repos and refreshes the command.
# Honors AIOS_HOME (default ~/aios) and AIOS_BIN (default ~/.local/bin).
set -eu

GH="${AIOS_GH:-https://github.com/cjw0076}"
AIOS_HOME="${AIOS_HOME:-$HOME/aios}"
AIOS_BIN="${AIOS_BIN:-$HOME/.local/bin}"
# Repos with public remotes. GenesisOS has no public remote yet — skipped.
REPOS="myworld hivemind memoryOS CapabilityOS"

say()  { printf '\033[1;36m[aios]\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[aios] warning:\033[0m %s\n' "$1" >&2; }
die()  { printf '\033[1;31m[aios] error:\033[0m %s\n' "$1" >&2; exit 1; }

# --- 1. prerequisites -------------------------------------------------------
command -v git >/dev/null 2>&1 || die "git is required — install git first."
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || die "python3 (>= 3.10) is required — install Python first."
PYV=$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo 0.0)
case "$PYV" in
  3.1[0-9]|3.[2-9]*|[4-9].*) : ;;
  *) warn "Python $PYV detected; AIOS targets >= 3.10. Continuing anyway." ;;
esac
say "prerequisites ok (git, $PY $PYV)"

# --- 2. clone or update the AIOS repos -------------------------------------
mkdir -p "$AIOS_HOME"
failed=""
for repo in $REPOS; do
  dest="$AIOS_HOME/$repo"
  if [ -d "$dest/.git" ]; then
    say "updating $repo"
    git -C "$dest" pull --ff-only --quiet 2>/dev/null || warn "could not fast-forward $repo (local changes?) — left as-is"
  else
    say "cloning $repo"
    if ! git clone --quiet "$GH/$repo.git" "$dest" 2>/dev/null; then
      warn "could not clone $repo from $GH/$repo.git"
      failed="$failed $repo"
    fi
  fi
done
[ -d "$AIOS_HOME/myworld/bin/aios" ] 2>/dev/null || true
[ -f "$AIOS_HOME/myworld/bin/aios" ] || die "myworld did not install — cannot continue (failed:${failed:- none})."

# --- 3. install the `aios` command -----------------------------------------
if ! mkdir -p "$AIOS_BIN" 2>/dev/null; then
  die "cannot create bindir $AIOS_BIN — set AIOS_BIN to a writable dir and retry."
fi
shim="$AIOS_BIN/aios"
cat > "$shim" <<EOF
#!/bin/sh
# AIOS launcher shim — installed by install.sh
exec "$AIOS_HOME/myworld/bin/aios" "\$@"
EOF
chmod +x "$shim"
say "installed: $shim"

# --- 4. PATH check ----------------------------------------------------------
case ":$PATH:" in
  *":$AIOS_BIN:"*) : ;;
  *) warn "$AIOS_BIN is not on PATH — add this to your shell profile:"
     printf '       export PATH="%s:$PATH"\n' "$AIOS_BIN" >&2 ;;
esac

# --- 5. done ----------------------------------------------------------------
if [ -n "$failed" ]; then
  warn "some repos did not clone:$failed (GenesisOS has no public remote and is expected to be absent)"
fi
say "AIOS installed at $AIOS_HOME"
say "next:  aios setup apply      # provision local models + config + service"
say "       aios self-model build # see what AIOS knows about itself"
