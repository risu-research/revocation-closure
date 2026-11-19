#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" != "dev" && "${1:-}" != "holdout" ]]; then
  echo "Usage: bash experiments/trusted_custody/run.sh {dev|holdout}" >&2
  exit 2
fi
PART="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="_custody_runs/$PART"
mkdir -p "$ROOT/$OUT"

docker run --rm --network host -v "$ROOT:/work" -w /work \
  -e PART="$PART" -e OUT="$OUT" \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
  sh -c '
    set -eu
    uv venv /tmp/shared-langgraph --python python3.12
    uv pip install --python /tmp/shared-langgraph/bin/python "langgraph==1.2.12"
    chmod -R a+rX /tmp/shared-langgraph
    /tmp/shared-langgraph/bin/python experiments/trusted_custody/integrated_driver.py --partition "$PART" --out "/work/$OUT"
    /tmp/shared-langgraph/bin/python experiments/trusted_custody/independent_auditor.py --db "/work/$OUT/ledger.sqlite" --oracle "/work/$OUT/oracle.json" --snapshots "/work/$OUT/sealed_candidate_snapshots.json" --out "/work/$OUT/audit.json"
    chown -R "$HOST_UID:$HOST_GID" "/work/$OUT"
  '
echo "Audited synthetic result: $ROOT/$OUT/audit.json"
