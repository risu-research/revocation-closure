# Retrospective source recovery

The forensic reanalysis behind Section V.D of *After the Clawback* uses the same 180 development and 540 held-out tool-read records as the observed-read evaluation. It tests whether a registered output hash and saved nonce identify an input sequence among six predeclared candidates: R, K, RR, RK, KR and KK. R and K are fixed synthetic source snapshots. Recovery of the sequence is checked separately from the body written to SQLite.

## Reproduce the archived analysis

The `evidence/` directory contains base64-encoded original development and held-out GitHub Actions evidence archives. They preserve the SQLite databases, read-event logs, transformation nonces, withheld oracle manifests, write acknowledgments and independent audit outputs. The two archives have SHA-256 digests:

- `trace824-development.zip`: `0995bdd607f751f2296547dae652e7ce8622aa0f372af630a17f4e4629fb13e3`
- `trace824-heldout.zip`: `874578de56ea671a111bd7435581cfb4a39757f0bf71d50f7a0ac5c025aa13d9`

With Python 3.12 or newer and standard `base64`, `unzip`, and `sha256sum`, run from the repository root:

```bash
bash experiments/retrospective_recovery/reproduce_archived.sh
```

The independently recomputed historical JSON has SHA-256 `7cdedd21980166346fed6889691cdd859a942ca2a180be32e539cfccf5acfd76`. The verifier checks the original data hashes, each stored SQL effect and oracle record, all 720 candidate-sequence results, and the four missing-evidence controls. The negative controls alter a disposable SQLite copy and must be rejected.

## Reproduce with fresh executions

The [observed-read runner](../observed_tool_reads/run.sh) generates a new database with fresh random nonces. The full public workflow runs the development partition, reuses the separately completed held-out partition, and runs `reproduce_fresh.py` against both. It checks the same invariants and archives the newly generated per-record results. For a local run, install `langgraph==1.2.12`, run the observed-read runner for both `dev` and `holdout`, then invoke:

```bash
python experiments/retrospective_recovery/reproduce_fresh.py \
  --dev experiments/observed_tool_reads/_runs/dev \
  --holdout experiments/observed_tool_reads/_runs/holdout \
  --out /tmp/recovery-fresh.json
```

Expected counts are 180/180 and 540/540 uniquely recovered with both candidates; removing R leaves 84 and 252 uniquely recovered, respectively, with 96 and 288 unresolved. The held-out record contains 36 untracked revoked-only reads, 36 partially untracked mixed reads, 36 tampering scenarios, and 24 altered SQL writes. These are reanalyses of designed source-read scenarios, not an additional cohort of legal cases. A source sequence is uniquely identified only within the specified candidate inventory.
