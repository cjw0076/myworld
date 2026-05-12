#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_COEVOLUTION_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT"

python scripts/aios_primitives.py monitor start --name aios-memory-pulse \
  --command 'while true; do bash scripts/aios_coevolution/memory_pulse.sh; sleep 1800; done' --json
python scripts/aios_primitives.py monitor start --name aios-capability-pulse \
  --command 'while true; do bash scripts/aios_coevolution/capability_pulse.sh; sleep 3600; done' --json
python scripts/aios_primitives.py monitor start --name aios-hive-pulse \
  --command 'while true; do bash scripts/aios_coevolution/hive_pulse.sh; sleep 900; done' --json
