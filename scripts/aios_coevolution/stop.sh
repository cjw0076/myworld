#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_COEVOLUTION_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT"

python scripts/aios_primitives.py monitor stop --name aios-memory-pulse --json
python scripts/aios_primitives.py monitor stop --name aios-capability-pulse --json
python scripts/aios_primitives.py monitor stop --name aios-hive-pulse --json
