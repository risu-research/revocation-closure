# Recipient acknowledgment and persisted-effect re-audit

The [independent-recipient experiment](../experiments/independent_recipient/PROTOCOL.md) distinguishes an owner's simulated source restriction in the withheld oracle from a policy update actually acknowledged by the separate HTTP/SQLite recipient. Its source code and original archives are described in [RECIPIENT_AUTHORITY_EVIDENCE.md](RECIPIENT_AUTHORITY_EVIDENCE.md).

## Original frozen evidence

| Split | Actions execution | Artifact | Replays | Physical SQL writes | SQLite SHA-256 |
| --- | --- | --- | ---: | ---: | --- |
| Development | [44467270022](https://github.com/risu-research/formal-exec-2609/actions/runs/44467270022) | 14502592760 | 192 | 132 | `3ef34bf9e0c92374df1fa4243e1c6de1407608fb809d96fc6e81937bec71cc0f` |
| Held-out | [44467406356](https://github.com/risu-research/formal-exec-2609/actions/runs/44467406356) | 14503131178 | 576 | 396 | `3df188a1aeab62723ac34e2a64db4d1e5ee81cdd275b5243f4288016c05e306b` |

The independently saved read-only audit results have SHA-256 `9cbfcae9e4152703c6fea04d543f7dd9bfdabe37b239b2a301feea28dfc98f9a` (development) and `eeeaf64d70b3000c3d03cf8d8ef3bd6c6bbf635a6d3c59ff3a969d8420d9ff7c` (held-out). A [public fresh-checkout reproduction](https://github.com/risu-research/formal-exec-2609/actions/runs/44467998371) independently rechecked the held-out archive and reproduced the development counts.

## Held-out result by event boundary

All figures in the table count actual stored SQL rows. Each mode has 144 scenario replays from twelve fixed scenarios, two policy fixtures and six held-out seeds.

| Recipient mode | Unsafe after owner's restriction | Unsafe after recipient acknowledgment | All SQL writes | Valid clean-control writes |
| --- | ---: | ---: | ---: | ---: |
| Open endpoint | 60 | 48 | 156 | 36 |
| Signed permit with no current-policy check | 48 | 36 | 96 | 24 |
| Recipient's current-policy check | 24 | 12 | 72 | 24 |
| Current policy plus owner credential | 24 | 12 | 72 | 24 |

The original protocol records owner-side revocation as an oracle fact. A delivered `/revoke` request creates a new acknowledgment epoch in the recipient-owned `events` and `cases` tables. In the `revocation_not_delivered` control, the oracle marks R restricted but the recipient remains at epoch 0. This is a fixed event-order scenario rather than a measured real-world delivery latency.

In each current-policy mode, the 24 unsafe effects after the owner event comprise **12 `false_clean_issuance` cases** and **12 `revocation_not_delivered` cases**. The former carry an issuer-authenticated K-only claim even though the withheld oracle records R. The latter retain the genuinely issued R claim, but the recipient never acknowledges the update. Accordingly, only the 12 false-issuance cases appear in the unsafe-after-acknowledgment column.

The owner-credential mode rejected every one of the 144 direct worker attempts. The underlying SQL decisions record 96 `NO_OWNER_WRITE_AUTHORITY` denials. The other 48 requests failed the earlier permit, output-integrity, or audience checks, before the owner-credential test. The relay then sent the mediated request with its own credential, and recipient policy verification still applied. This makes the 144 direct denials a result of the combined receiving checks, not 144 independent credential-specific failures.

The open endpoint committed 156 effects from 144 replays because its 12 `duplicate_clean` scenarios each wrote twice. The signed-permit modes admitted a single clean write in those cases and refused its duplicate.

## Record-level checks

The archived SQL rows were checked against the original oracle source truth, each initially issued permit, the recipient's policy-event sequence, the written body, the recipient epoch and the entire per-case response chain. The development and held-out SQLite integrity checks passed, and the complete output counts matched the separately recorded first-pass audits.

Disposable copies of the held-out database were modified in three ways: changing a stored effect body, altering an acknowledged revocation event, and replacing an issued source label. Independent record-level checks rejected each altered copy.

## Reproduction

Download the original Actions artifact ZIPs above, extract their `_recipient_dev/` and `_recipient_holdout/` directories and run the published read-only observer with the saved database, oracle and response records:

```bash
python experiments/independent_recipient/independent_auditor.py \
  --db /path/to/_recipient_holdout/recipient.sqlite \
  --oracle /path/to/_recipient_holdout/oracle.json \
  --responses /path/to/_recipient_holdout/responses.json \
  --out /tmp/recipient-recomputed.json
```

The [public reproduction guide](../REPRODUCING.md) also explains how to run fresh synthetic checkpoints using the public scripts. No private credentials or authentic client data are included in these artifacts.
