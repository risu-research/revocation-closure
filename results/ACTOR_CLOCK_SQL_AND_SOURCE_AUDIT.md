# Actor, clock, and recipient-effect source audit

The [actor-clock experiment](../experiments/actor_clock/README.md) applies eight selected court-order duties to a separately running SQLite recipient. This audit cross-checks their source clauses against the exact entered orders and independently reads the physical records from a newly reproduced Linux-UID-separated execution.

## Source-linked duty register

The original [eight-entry register](../experiments/actor_clock/source_stage_n/R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER.csv) has these legal anchors:

| Order | Provision | Responsible actor in selected fixture | Clock start | Period |
| --- | --- | --- | --- | --- |
| [iOttie](https://cases.justia.com/federal/district-courts/new-york/nysdce/1:2025cv02642/639666/59/0.pdf) | §9.2 producer log/replacement | Producing party | Producer informs receiver of inadvertent production | 10 business days |
| iOttie | §9.2 retained challenge copy | Receiving challenger | Receipt of log identification and any applicable redacted replacement | 7 business days |
| iOttie | §19 final disposition | Receiving party instance | Final termination including appeals, or expiry of appeal period | 2 months |
| [Camm](https://cases.justia.com/federal/district-courts/new-york/nysdce/1:2025cv01921/638232/38/0.pdf) | §20 inadvertent disclosure | Receiving party | Receipt of producer notice | 5 business days |
| Camm | §11(b) final return | Receiving party | Conclusion of litigation including appeals | 60 days |
| [Napoli](https://cases.justia.com/federal/district-courts/new-york/nysdce/1:2025cv02872/640129/37/0.pdf) | §13 privilege disposition | Receiving party | Producer notice | 7 days |
| Napoli | §10 final disposition | Receiving party | Final termination | 30 days |
| Napoli | §10 confirmation | Receiving counsel | Return or destruction | 10 days |

For the iOttie §19 final-disposition duty, the court order addresses each party. The test implements the receiving-party instance. Under Napoli §13, self-discovery requires immediate non-use and sequestration; the seven-day disposition clock has the distinct producer-notice start event. The fixture records this separation. Archive eligibility is evaluated using the recipient's preapproved synthetic classification records. The selected restricted-storage route exercises the exception without representing retention of real client documents.

## Reproduced execution and archived evidence

- [Successful Actions execution 44850698844](https://github.com/risu-research/revocation-closure/actions/runs/44850698844), commit `572791d3ee132a1142207f3fbf28351e4fca0349`.
- [Synthetic SQL evidence artifact 14684823406](https://github.com/risu-research/revocation-closure/actions/runs/44850698844/artifacts/14684823406), containing all six recipient-owned SQLite files, event envelopes, test dates, scenario results, snapshots, and the original independent audit.
- [Reproduction workflow](../.github/workflows/verify-actor-clock.yml) checks the published source hashes, runs the twelve date unit tests, creates six isolated recipient instances, reruns the original independent auditor, and archives file digests.

| Recorded item | Reproduced result |
| --- | ---: |
| Recipient instances and separate SQLite files | 6 |
| Scenario outcomes | 29 |
| External-effect requests | 17 |
| External SQL effect rows | 5 |
| Blocked effect requests | 7 |
| Held effect requests | 5 |
| Actor-signed legal-event attempts | 17 |
| Accepted events | 15 |
| Rejected actor-signature or replay events | 2 |
| Duty-date assertions | 17 |
| Additional policy-boundary assertions | 3 |
| Restricted challenge-copy authorization records | 1 |
| Restricted counsel-archive authorization records | 3 |

Among the five effects, four were consistent with the recipient's recorded restrictions. The fifth was the deliberately omitted-notice Napoli control, in which the withheld oracle knew the output depended on a protected source but the recipient held no corresponding notice. The iOttie challenge tests accepted one single-copy authorization record and held three requests, covering a duplicate, a wrong actor, and a late request. Archive tests recorded three selected restricted-retention authorizations and held four others, including an assertion that contradicted the recipient's pinned confidential-content classification.

The deadline test separates producer notice from receipt of a log and replacement, source self-discovery from producer notice, and return/destruction from written confirmation. The recipient timestamps accepted events with its own simulated clock. In this fixture the controlled business-day calendar excludes 2026-11-26 and 2026-12-25; a missing-calendar test yields `UNRESOLVED_CALENDAR` rather than a guessed deadline. Written completion claims are represented by separately signed actor events.

## Independent check of saved SQL

The stored recipient database effects were compared with the original Stage Q signed source, program and output bundles. For every committed effect, the archived output digest matches its two valid broker signatures, and the recipient actor authorization signature is valid. Every accepted legal event was also signature-checked against its role and case. The saved SQL includes signed authority records for one iOttie challenge-copy reservation and three counsel-retention requests. Those records identify permissions; the test does not store protected documents or conduct a real destruction operation.

Five disposable mutation controls changed a stored effect digest, a recorded notice date, a retained-item classification digest, a challenge-copy signature, or a legal-event signature. Each was rejected during an independently written read-only audit. The original Actions archive remained unchanged.

The source and audit inputs are public. From the repository root, run the [documented reproduction commands](../experiments/actor_clock/README.md) or trigger the Actions workflow manually.
