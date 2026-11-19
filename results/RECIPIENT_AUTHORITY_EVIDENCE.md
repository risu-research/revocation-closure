# Original evidence for recipient-owned revocation enforcement

## Final source

The five source files in [experiments/independent_recipient](../experiments/independent_recipient) were frozen before the held-out evaluation. The full experimental source includes:

- Recipient service Git blob: `bff0dbbfce5f3b98da3eee53796fb7926803e64a`
- Owner relay: `ebb75cb3ed9e86766ea4384a5e332e930a09aef2`
- Untrusted LangGraph worker: `2a192d3fe53fc5d88a7c29127c7707ba3aa0e488`
- Test runner and oracle builder: `a99a261b49c23d7cb812124822e5639e304c8c51`
- Independent read-only auditor: `aaeabbea60c589e30db2c60bbbed6b19bab29644`

## Completed GitHub Actions

| Activity | Run | Original archive | Checks |
| --- | --- | --- | --- |
| Development | [44467270022](https://github.com/risu-research/formal-exec-2609/actions/runs/44467270022) | [14502592760](https://github.com/risu-research/formal-exec-2609/actions/runs/44467270022/artifacts/14502592760) | 192 replay cases, 132 physical writes |
| Held-out evaluation | [44467406356](https://github.com/risu-research/formal-exec-2609/actions/runs/44467406356) | [14503131178](https://github.com/risu-research/formal-exec-2609/actions/runs/44467406356/artifacts/14503131178) | 576 replay cases, 396 physical writes |
| Fresh public checkout and original held-out re-audit | [44467998371](https://github.com/risu-research/formal-exec-2609/actions/runs/44467998371) | [14503231835](https://github.com/risu-research/formal-exec-2609/actions/runs/44467998371/artifacts/14503231835) | Same 192-case development totals, held-out 576-case re-audit and SQL mutation negative control |

The public reproduction job cloned the public repository at commit `1d65e72d95cfdf50e81de95943615438eed7261d` and ran its published `run.sh dev` with a freshly created Linux-UID-separated service stack. It confirmed all development results. Its separately fetched original held-out SQLite, oracle and response records were recomputed with the public independent auditor, yielding byte-for-byte identical JSON.

## Independently audited archived data

| Split | SQLite SHA-256 | Audit JSON SHA-256 |
| --- | --- | --- |
| Development | `3ef34bf9e0c92374df1fa4243e1c6de1407608fb809d96fc6e81937bec71cc0f` | `9cbfcae9e4152703c6fea04d543f7dd9bfdabe37b239b2a301feea28dfc98f9a` |
| Held-out | `3df188a1aeab62723ac34e2a64db4d1e5ee81cdd275b5243f4288016c05e306b` | `eeeaf64d70b3000c3d03cf8d8ef3bd6c6bbf635a6d3c59ff3a969d8420d9ff7c` |

Both original Actions ZIP archives were downloaded and extracted in a separate container-backed environment. Their SQLite integrity checks and physical effect counts passed. The independent read-only auditor reproduced both archived JSON reports exactly. A copy with a modified physically persisted effect body was rejected in both splits.

The full machine-readable summary is at [recipient_authority_summary.json](recipient_authority_summary.json).

## Why the remaining failures matter

For the 144 held-out examples in each recipient mode, receiver current-policy checking produced only 24 unsafe physical effects after the simulated owner notice. It did **not** reach zero across the full matrix.

The 24 events divide into two conditions fixed before evaluation:

- 12 false original issuer claims. The output depended on R, but the authorized issuer issued a permit attesting only K.
- 12 unacknowledged owner notices. The real-world owner state had changed in the test oracle, but the independent recipient policy had not received that change.

When the recipient had **acknowledged revocation** and original provenance was accurate, `live` and `owner_live` refused all newly prohibited R-derived effects. The recipient's local `BEGIN IMMEDIATE` transaction ensures the policy and the physical effect are ordered together at that recipient. It does **not** ensure instantaneous legal notice delivery across arbitrary systems.

A separate owner credential prevented all direct attempts by the untrusted worker against that recipient. A worker with a valid capability was still able to request the trusted relay to act on its behalf, and the relay's recipient-side policy check remained necessary. This is a failure-prevention boundary, not a universal network-sandbox guarantee.

This module does not alter the accepted manuscript or original 96/96 controlled repair results. No release, Zenodo deposit or DOI was created or approved.
