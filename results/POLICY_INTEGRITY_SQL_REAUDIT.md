# Recipient current-permission and policy-integrity SQL re-audit

The [policy-integrity experiment](../experiments/policy_integrity/README.md) has two distinct checks. The receiving service consults its current, acknowledged source restrictions for every protected-source write, including the `static` permit path. A separate startup validation checks the selected typed court-policy record, and the result controls whether an affected protected write may commit. Both mechanisms use the recipient's own SQLite transaction at the final effect boundary.

## Pinned source and fresh archive

- [Successful Actions run 44853643589](https://github.com/risu-research/revocation-closure/actions/runs/44853643589), based on commit `e72b75691c983ca3b06f40b510537dcd7070e94e`.
- [Artifact 14687010433](https://github.com/risu-research/revocation-closure/actions/runs/44853643589/artifacts/14687010433) retains two fresh reproductions. Each includes the original and guarded recipient runs, five actual SQLite databases per recipient, signed requests, the independent SQL auditors' inputs, a detailed case comparison, policy-mutation results, and a stored-SQL tampering control.
- The [reproduction workflow](../.github/workflows/verify-policy-integrity.yml) verifies all **29** original source hashes in [SOURCE_SHA256.json](../experiments/policy_integrity/SOURCE_SHA256.json), regenerates the 18-rule/eight-duty typed policy, and checks it against the fixed policy hash before running tests.
- During this re-audit the eight-duty CSV in `inputs/R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER_original.csv` was restored to the exact CRLF bytes of the [existing court-duty source register](../experiments/actor_clock/source_stage_n/R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER.csv). Its nine rows were text-identical before restoration. The recorded `693ba4be4385873a39b038266b11869fccedc74f11398b8765f1eb10f57624cf` SHA-256 now matches the actual bytes; the independent rebuild no longer fails.
- The checksum workflow was also corrected to exclude its own output manifest from the hash list. All **75** archived file hashes per fresh run were independently matched against the extracted bytes.

## The five changed decisions

The same 46 designed document-to-effect cases were run using the original and strengthened services. New keys and, where policy-linked note generation differs, new signed output bytes are generated for each branch. The experiment matches cases by fixture and scenario rather than treating independent signatures as byte-identical.

| Measure per full reproduction | Original recipient | Strengthened recipient |
| --- | ---: | ---: |
| HTTP write requests | 46 | 46 |
| Stored SQL effects | 17 | 12 |
| Oracle-unsafe effects | 9 | 4 |
| Legitimate effects preserved | 8 | 8 |
| Blocks due to fresh current-permission check | 0 | 5 |

Exactly five decisions changed from `ALLOW` to `BLOCK_A0_REVOKED`.

| Case | Scenario | Original | Strengthened |
| --- | --- | --- | --- |
| Camm | `stale_signed_permit` | Allow | Block |
| Camm | `mixed_static` | Allow | Block |
| Napoli | `stale_signed_permit` | Allow | Block |
| Napoli | `mixed_static` | Allow | Block |
| Napoli | `self_discovery_cached_unsafe` | Allow | Block |

All five carried static-mode permissions that previously bypassed the recipient's current source restriction. At the strengthened receiving service, the `A0Gate` checks for revoked observed protected sources during the same `BEGIN IMMEDIATE` write transaction as the SQL insertion.

The four remaining unsafe stored rows comprise two `unobserved_source_bypass` controls, in which protected text was appended after the instrumented source reads, and two `notice_not_delivered` controls, in which the recipient held no acknowledged restriction. The same four cases remained in both fresh reproductions.

## Separate structural-policy mutation tests

The selected typed representation carries 18 source-linked rules and eight actor/deadline duties. The [source policy validator](../experiments/policy_integrity/src/a0_assurance.py) checks it against the pinned records. The 13 injected changes were:

1. Wrong actor
2. Missing actor
3. Business-day unit changed
4. Camm deadline removed
5. Napoli notice-clock trigger changed
6. Napoli 30-day final period removed
7. Napoli 10-day confirmation period removed
8. iOttie challenge-copy scope widened
9. Court-document locator replaced
10. Rule's triggering events changed
11. Original rule deleted
12. Selected-scope disclosure removed
13. Clock record escalated into write permission

The structural validator flagged all 13. Twelve mutations were also tested by fresh HTTP/SQLite recipients with previously signed requests. Each recipient held its protected-source request (`HOLD_A0_UNVERIFIED_POLICY`) and saved one independently clean effect (`ALLOW`). The iOttie challenge-copy alteration was tested structurally only because the document-to-effect matrix has no corresponding signed iOttie document request.

The receiver's structural status is created at startup, while the affected write decision and current-revocation test take place at its SQLite write boundary. These are distinct from the actor-and-clock runtime experiment and from the legal interpretation of the original court clauses.

## Independent archived-record checks

Both complete reproductions passed their original read-only SQL auditors and a separate case-and-SQL audit. The latter compared all 92 cross-version scenario rows, all 184 recipient attempt records, the actually stored content and local digests, the signed request archives, and the detailed policy-mutation results. It found the same five changes and the same four remaining unsafe cases in both runs.

The supplied negative control modified a stored SQL body **and its local hash**; the original independent auditor rejected the altered evidence. The original generated data and source files were retained unchanged.

Use the public [reproduction entry point](../experiments/policy_integrity/reproduce.py) or the Actions workflow to regenerate the result from the pinned inputs.
