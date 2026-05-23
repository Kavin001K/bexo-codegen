#!/bin/bash
# BEXO autonomous build — invoked locally or from Cloud Run via build_engine.py
set -euo pipefail

PROFILE_ID="${1:?profileId required}"
HANDLE="${2:?handle required}"

cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

python3 -c "
from build_engine import run_build
lines = run_build('${PROFILE_ID}', '${HANDLE}')
for line in lines:
    print(line)
"
