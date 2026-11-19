#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ "$#" -lt 1 ]]; then
  echo "Usage: bash experiments/external_effects/run.sh {dev|holdout} [output-directory]" >&2
  exit 2
fi
PART="$1"
if [[ "$PART" != dev && "$PART" != holdout ]]; then
  echo "Unknown partition: $PART" >&2
  exit 2
fi
if [[ "$#" -ge 2 ]]; then OUT="$2"; else OUT="$ROOT/_runs/$PART"; fi
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
PORT="$(printenv REVOCATION_TEST_PORT || echo 8765)"
cd "$OUT"

python3 "$ROOT/external_effect_runner.py" --partition plan
python3 "$ROOT/external_effect_sink.py" --db "$OUT/effects.sqlite" --port "$PORT" > sink.log 2>&1 &
SINK_PID=$!
trap 'kill "$SINK_PID" 2>/dev/null || true' EXIT
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null

python3 "$ROOT/external_effect_runner.py" --partition "$PART" --endpoint "http://127.0.0.1:$PORT" | tee replay.log
kill "$SINK_PID"
wait "$SINK_PID" || true
trap - EXIT

python3 - <<'PY'
import sqlite3
with sqlite3.connect("effects.sqlite") as c:
    state=c.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    assert state[0]==0, state
    mode=c.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
    assert mode.lower()=="delete", mode
    assert c.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    print("ARCHIVED_SQL_WRITES",c.execute("SELECT COUNT(*) FROM writes").fetchone()[0])
PY

python3 "$ROOT/external_effect_auditor.py" --db effects.sqlite --oracle "external_effect_$PART""_oracle.json" --acks "external_effect_$PART""_acks.json" --out "external_effect_$PART""_audit.json" | tee audit.log
sha256sum effects.sqlite "external_effect_$PART""_audit.json" > SHA256SUMS.txt
echo "Wrote reproducible evidence to $OUT"
