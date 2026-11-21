# Archived SQL re-audit of the external-effect receiver

The [external-effect experiment](../experiments/external_effects/PROTOCOL.md) compares cached approval, a client-side policy precheck, and a receiver-side check performed inside a SQLite write transaction. Its two original Actions archives contain the complete synthetic oracle manifests, workflow acknowledgments, effect databases, and first-pass read-only audit reports.

## Original evidence

| Split | Actions run | Artifact ID | Replays | Stored SQL writes | SQLite SHA-256 |
| --- | --- | --- | ---: | ---: | --- |
| Development | [44457578111](https://github.com/risu-research/formal-exec-2609/actions/runs/44457578111) | 14498955334 | 384 | 240 | `f90e8f8f4fd96759c737c2cdf0a0e9c7116f0ffa5aac874a6f96f5bd55ec0517` |
| Held-out | [44457583262](https://github.com/risu-research/formal-exec-2609/actions/runs/44457583262) | 14498647239 | 1,152 | 720 | `4afcea6dc602a1ca4b2253aa42b55e5b92fa0a8796667a994cd04bf748b23e5a` |

The recorded first-pass audit SHA-256 values are `61db45b7867e43809423250070009ce18c07192314f8c0e467856baf646a6889` (development) and `ab72f0745536447ee031021b9111f6f205de62359075ddaa8d1a6413098e4cbf` (held-out).

Both final archives contain SQLite databases with completed WAL checkpoints and passing integrity checks. The original workflow, receiver, and independent observer are pinned by their Git blob hashes in [external_effects_summary.json](external_effects_summary.json).

## Held-out results

Each guard was applied to 16 fixed scenarios under two manually specified legal-policy fixtures and 12 held-out seeds. This gives 384 replays per guard, split into 216 restricted-source cases, 120 clean-source cases, and 48 pre-notice or post-release authorization controls.

| Guard | Prohibited SQL writes | Clean SQL writes | Unsafe race writes | Unresolved decisions |
| --- | ---: | ---: | ---: | ---: |
| Cached approval | 216 / 216 | 120 / 120 | 48 / 48 | 0 / 384 |
| Client precheck | 96 / 216 | 48 / 120 | 48 / 48 | 120 / 384 |
| Receiver atomic check | 48 / 216 | 48 / 120 | 0 / 48 | 120 / 384 |

The 48 restricted-source race cases consist of 24 `revoke_after_client_check` runs and 24 `mixed_during_revocation` runs. The test arranges the receiver's policy update between the client's successful `/authorize` request and its later `/write_unguarded` request. The receiver's `/write_atomic` operation evaluates the current policy and the receipt inside the same `BEGIN IMMEDIATE` transaction as the insert.

The 48 remaining unsafe writes under the atomic guard split evenly between `false_complete_clean_label` and `mixed_with_omitted_revoked`. Both have source R in the withheld oracle truth and only source K in the asserted receipt.

Of the receiver's 120 clean-source cases, 48 committed. The other 72 consist of 24 missing-receipt cases, 24 stale-digest cases, and 24 cases with a false R label. In each of the client-precheck and atomic modes, 120 of all 384 cases returned an unresolved decision.

## Independent record check

The new [archive verifier](../tests/verify_external_effect_archives.py) reads the original SQLite files in read-only mode and reconstructs every per-case decision from the manifest and archived event history. It checks all 1,536 development and held-out cases, physical payloads, policy epochs, receipt contents, unique identifiers, workflow acknowledgments, and the archived observer's individual records. Its recorded totals match both original first-pass audits.

Download and extract the two Actions artifact ZIPs into separate directories, then run:

```bash
python tests/verify_external_effect_archives.py \
  --dev /path/to/development-artifact \
  --holdout /path/to/heldout-artifact \
  --out external_effect_reaudit.json
```

A disposable copy of the held-out SQLite file was modified by changing a stored write payload. The new verifier rejected the altered row. The original archive remains unchanged.

These are fixed synthetic fault scenarios using a local HTTP receiver with a separate SQLite database. The held-out counts compare decisions and persisted writes under the specified conditions.
