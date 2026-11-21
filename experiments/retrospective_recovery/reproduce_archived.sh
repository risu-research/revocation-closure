#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
for part in development heldout; do
  base64 --decode "$HERE/evidence/trace824-${part}.zip.b64" > "$TMP/${part}.zip"
done
printf '%s  %s\n' \
  0995bdd607f751f2296547dae652e7ce8622aa0f372af630a17f4e4629fb13e3 "$TMP/development.zip" \
  874578de56ea671a111bd7435581cfb4a39757f0bf71d50f7a0ac5c025aa13d9 "$TMP/heldout.zip" \
  | sha256sum --check --status
unzip -q "$TMP/development.zip" -d "$TMP/dev"
unzip -q "$TMP/heldout.zip" -d "$TMP/holdout"
python3 "$HERE/audit_retrospective_recovery.py" \
  --dev "$TMP/dev/_runs/dev" \
  --holdout "$TMP/holdout/_runs/holdout" \
  --out "$TMP/recomputed.json"
printf '%s  %s\n' \
  7cdedd21980166346fed6889691cdd859a942ca2a180be32e539cfccf5acfd76 "$TMP/recomputed.json" \
  | sha256sum --check --status
python3 "$HERE/test_recovery_mutation.py" --dev "$TMP/dev/_runs/dev"
echo 'PASS: historical retrospective recovery and corruption controls'
