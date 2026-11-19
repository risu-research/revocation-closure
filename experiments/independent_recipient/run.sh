#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" != "dev" && "${1:-}" != "holdout" ]]; then
  echo "Usage: bash experiments/independent_recipient/run.sh {dev|holdout}" >&2
  exit 2
fi
PART="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$ROOT/_recipient_runs/$PART"

docker run --rm --network host -v "$ROOT:/work" -w /work \
  -e PART="$PART" ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
  sh -c '
    set -eu
    uv venv /tmp/recipient-venv --python python3.12
    uv pip install --python /tmp/recipient-venv/bin/python "langgraph==1.2.12"
    chmod -R a+rX /tmp/recipient-venv
    /tmp/recipient-venv/bin/python experiments/independent_recipient/run_evaluation.py \
       --partition "$PART" --isolated-uids --out "/work/_recipient_runs/$PART"
    /tmp/recipient-venv/bin/python experiments/independent_recipient/independent_auditor.py \
       --db "/work/_recipient_runs/$PART/recipient.sqlite" \
       --oracle "/work/_recipient_runs/$PART/oracle.json" \
       --responses "/work/_recipient_runs/$PART/responses.json" \
       --out "/work/_recipient_runs/$PART/audit.json"
  '
echo "Independent recipient audit: $ROOT/_recipient_runs/$PART/audit.json"
