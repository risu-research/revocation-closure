# Audited source reads, preissued permits, and recipient SQL effects

The [document-to-effect experiment](../experiments/document_to_effect/README.md) reads locally frozen court-order descriptions and synthetic discovery records through a real HTTP source service. Signed source receipts, issuer permits, and actor notices are delivered to separate HTTP/SQLite recipients. The auditor checks the physical rows.

## Court-source anchors

The selected public inputs cite [*Camm v. Reach Financial*, Dkt. 38, §20](https://cases.justia.com/federal/district-courts/new-york/nysdce/1:2025cv01921/638232/38/0.pdf), and [*Napoli v. Meta Platforms*, Dkt. 37, §13](https://cases.justia.com/federal/district-courts/new-york/nysdce/1:2025cv02872/640129/37/0.pdf). The fixed [source snapshot](../experiments/document_to_effect/inputs/source_snapshot.json) contains short exact phrases and researcher-written procedural summaries. The rest of the source records are invented.

A record-level review identified a narrow text-matching defect in the original deterministic worker. The *Camm* snapshot used `five (5) business days`, but `agent.py` originally looked only for `five business days`. As a result, the four Camm worker-generated notes and one post-read modified control had displayed `unresolved legal clock`. The [corrected worker](../experiments/document_to_effect/code/agent.py) recognizes both formulations. The [regression tests](../experiments/document_to_effect/tests/test_clause_note.py) check the five-business-day *Camm* and seven-day *Napoli* note text directly.

The correction changes the affected note bytes and new cryptographic hashes. It leaves the original archive intact and does not alter the 46 configured effect cases, recipient policy decisions, or aggregate counts.

## Fresh public reproduction

- [Successful corrected GitHub Actions run 44852112564](https://github.com/risu-research/revocation-closure/actions/runs/44852112564), from commit `5468405220571bc53b38d760b096f6b514ffa3a2`.
- [Full corrected evidence artifact 14685463136](https://github.com/risu-research/revocation-closure/actions/runs/44852112564/artifacts/14685463136) retains both fresh runs, including signed read receipts and permit requests, output documents, response timelines, five recipient SQL databases per run, and an independent audit report for each.
- The [Actions workflow](../.github/workflows/verify-document-to-effect.yml) pins the source manifest, runs two clause-regression tests, and executes and audits two full independent runs.
- [Earlier successful execution 44851850611](https://github.com/risu-research/revocation-closure/actions/runs/44851850611), artifact 14684719974, retains the pre-correction Camm notes as a historical comparison.

| Recorded result | Corrected run 1 | Corrected run 2 |
| --- | ---: | ---: |
| Source-service read rows | 18 | 18 |
| Signed issuer permits | 38 | 38 |
| Worker-generated notes | 8 | 8 |
| Post-read altered output controls | 2 | 2 |
| Recipient write requests | 46 | 46 |
| Physical SQL writes | 17 | 17 |
| Blocked for revocation | 13 | 13 |
| Blocked duplicate permits | 2 | 2 |
| Held for evidence failures | 14 | 14 |
| Unsafe effects in designed controls | 9 | 9 |
| Recipient SQLite databases | 5 | 5 |
| Signed actor-event envelopes | 7 | 7 |

The 17 stored effects comprise eight permitted clean or pre-notice writes and nine intentionally unsafe controls. The nine are two stale R-source static-permit writes, two mixed-source static-permit writes, two missed-notice writes, two outputs modified with protected literals after the observed read, and one Napoli self-discovery write with a static permit.

Across each trial, 20 permits were issued before an acknowledged source restriction and 18 after the first accepted notice in their respective case. One post-notice test specifically issued a fresh signed R-source permit and confirmed that a recipient using current policy rejected the write. The synthetic permit body keeps `issued_epoch=0` in both groups, so chronological ordering is checked from the separate archived issuance and notice sequence, not inferred from that field.

## Signature and SQL checks

The independent published observer and a second offline record checker confirmed 18 tool reads and their source signatures, 38 issuer signatures, 7 actor-event signatures, every permit-to-request relation, all 46 receiving decisions, and all 17 stored SQL outputs per run. They also verified that the recipient's existing SQLite policy blocked a protected write after the HTTP recipient was restarted.

Five disposable mutations targeted a stored output and its recomputed digest, the SQL read identifier's source, an issuer signature, a recipient notice record, and a source-read signature. All five were detected. No original artifact was changed.

The local read service returns snapshots of the two orders rather than fetching live docket documents. Outputs come from a deterministic worker. The test's hidden-input controls intentionally add text after those instrumented reads and show why the observed source set matters alongside signed permits and acknowledged recipient policy.
