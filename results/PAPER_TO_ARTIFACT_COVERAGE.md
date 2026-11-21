# Manuscript-to-artifact coverage audit

Paper: *After the Clawback: Revocation Closure in Agentic Legal Workflows*.
Source audited: R60, November 20, 2026. This is an evidence index, not part of the submitted manuscript.

Each row links a paper claim to fixed data or an executable verifier. Distinguish historical result reconstruction from re-execution with a newly generated run ID. The [full reproduction workflow](../.github/workflows/reproduce-full-artifact.yml) regenerates the experiment groups and makes a final independent check of stored SQL rows, hashes, and expected counts.

## Sections and tables

| Manuscript location | Fixed claims or scope | Public verification entry |
| --- | --- | --- |
| I. Introduction | 40 orders; later actions and clean dependent work | [Court-coded original and final matrices](../experiments/court_coding/README.md); [recipient experiments](SECTION_VI_CROSS_EXPERIMENT_EVIDENCE_MAP.md) |
| II.A, Table I | 30 core orders, original 13-code frequencies | [Frozen 520 labels](../experiments/court_coding/frozen_520.csv); [core verifier](../experiments/court_coding/verify_public_coding.py) |
| II.A, Table II | 40 orders, event-specific scope, 120 revisions and 378 final positives | [Conditional labels and revision ledger](../experiments/court_coding/CONDITIONAL_CODING.md); [conditional verifier](../experiments/court_coding/verify_conditional_coding.py) |
| II.B, Table III | Acosta 7/7, NECEC 8/8, Broadway 4/4, Spheres 6/6; eight checkpoint replays | [Court policy probe](../experiments/court_policy/legal_order_probe.py); [recorded assertions](court_policy_result.json) |
| II.C, Table IV | Six clause-to-policy cases over iOttie, Camm and Napoli | [Pinned policy and order sources](../experiments/actor_clock/README.md); [source corpus](../experiments/document_to_effect/inputs/COURT_SOURCES.md) |
| II.C, Table V | Eight actor-specific deadlines; amended source-pinned duty register | [Actor-clock duties](../experiments/actor_clock/source_stage_n/R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER.csv); [policy-integrity study](../experiments/policy_integrity/README.md) |
| II.D | 18 rules, 37 policy scenarios, 19 unit tests, six permitted and one false-source SQL effect; lexical transfer 20+8 duties | [Typed rules and standalone legal checks](../experiments/actor_clock/README.md); [court-order transfer](../experiments/court_order_transfer/README.md) |
| III | Conditional source and effect safety, A0–A4; deterministic source-removal reference | The criterion is a formal conditional specification. Its testable premises are isolated in the [provenance](../experiments/provenance_stress/PROTOCOL.md), [recipient](../experiments/independent_recipient/PROTOCOL.md), and [policy integrity](../experiments/policy_integrity/README.md) tests. The mathematical equality is not an additional reported dataset. |
| IV | Chroma, Qdrant, Haystack, LlamaIndex deletion; older LangGraph checkpoint retaining R in 3/4 snapshots | [Five exact original code files, recorded results and new executions](../experiments/component_history/README.md); [historical verifier](../experiments/component_history/verify_historical.py) |
| V.A–B, Table VI | 18 scenarios × 2 policies × 20 held-out seeds × 3 guards = 2,160; source-label and simulated receipt faults | [Provenance protocol](../experiments/provenance_stress/PROTOCOL.md); [stored summaries](PROVENANCE_STRESS_EVIDENCE.md) |
| V.C, Table VII | 540 observed HTTP reads, missing observations, SQL effects and nonces | [Observed reads](../experiments/observed_tool_reads/PROTOCOL.md); [physical audit](OBSERVED_TOOL_READ_EVIDENCE.md) |
| V.D | 180 development and 540 held-out retrospective six-candidate reconstructions; 252/288 snapshot-withheld split; tamper controls | [Original archived SQLite/read/oracle evidence](../experiments/retrospective_recovery/README.md); [independent auditor](../experiments/retrospective_recovery/audit_retrospective_recovery.py) |
| VI.A | Seven InMemorySaver and seven PostgresSaver original checkpoint-to-write cases; separate SQL effects | [Exact original runners and saved case-level SQL rows](../experiments/component_history/README.md); [new physical SQLite preservation](../experiments/component_history/retain_execution_sql.py) |
| VI.B, Table VIII | 1,152 physical write attempts, 720 persisted, 48 check/commit race effects prevented, 48 false-claim effects | [External effects protocol](../experiments/external_effects/PROTOCOL.md); [SQL verification](EXTERNAL_EFFECT_SQL_REAUDIT.md) |
| VI.C | 168 source custody conditions, 60 physical writes, untrusted UID access tests | [Custody protocol](../experiments/trusted_custody/PROTOCOL.md); [SQL evidence](TRUSTED_CUSTODY_EVIDENCE.md) |
| VI.D | 17 program attempts and recipient submissions, four vs five SQL effects, approved-program literal control | [Signed program binding](../experiments/program_binding/README.md); [reproduction audit](PROGRAM_BINDING_CI_AUDIT.md) |
| VI.E, Table IX | 576 recipient replays with owner event vs recipient acknowledgment; four modes | [Independent-recipient protocol](../experiments/independent_recipient/PROTOCOL.md); [actual effects](RECIPIENT_ACK_SQL_REAUDIT.md) |
| VI.F | 8 typed legal duties, 17 deadline checks, 17 attempts with 5 SQL effects, 4 restricted retention records | [Actor-clock module](../experiments/actor_clock/README.md); [source and SQL audit](ACTOR_CLOCK_SQL_AND_SOURCE_AUDIT.md) |
| VI.G | 46 new document-to-SQL attempts, 18 HTTP reads, 38 permits, 17 writes, 9 unsafe controls | [Document-to-effect module](../experiments/document_to_effect/README.md); [new execution audit](DOCUMENT_TO_EFFECT_CHAIN_AUDIT.md) |
| VI.H | Same fixed 46 scenarios, 17 vs 12 writes and 9 vs 4 unsafe; 13 detected policy mutations | [Policy-integrity module](../experiments/policy_integrity/README.md); [SQL audits](POLICY_INTEGRITY_SQL_REAUDIT.md) |
| VII–VIII | Interpretation, legal limitations and reproducibility record | [Full reproduction guide](../REPRODUCING.md); [all modules audit](PUBLIC_ARTIFACT_REPRODUCTION_AUDIT.md) |

## What is and is not a reproducible observation

- Court-order coding is a reviewed, purposively sampled legal dataset, not a random or independent blinded legal oracle. All entered orders, recorded code decisions and amended duty records have public source references. The complete original discovery-search query history is not available; do not claim prospective corpus enumeration from those 40 sources.
- Historical Chroma/Qdrant/Haystack/LlamaIndex and checkpoint source files match the original Git blob hashes. The original outcome records are preserved. New runs use the supported package versions and should be reported separately from the historical observations.
- The seven historical SQLite databases per checkpointer were created in a temporary directory in the original tests and not retained as raw bytes. Their per-case SQL rows were saved in the historical JSON. New re-executions preserve seven actual databases per backend; the independent auditor compares each database with those original recorded rows.
- The retrospective study reconstructs source sequences from a specified finite candidate set and known transformation plus nonce. Its 540/540 source-recovery count does not claim all downstream effects were acceptable: deliberate output-tampering controls are separately rejected.
- Actual authority in the governing legal order and completeness of unobserved source contributions are assumptions of the formal condition, not independently learned by the code.
- All studies use synthetic effects. Each test cohort and denominator is separate. The 46-case strengthened recipient comparison reuses the same scenario definitions, not an unrelated random legal sample.

## Continuous checks

Run the [full workflow](../.github/workflows/reproduce-full-artifact.yml). It invokes the separate historical-component reproduction, retrospective source recovery, court-coding and policy tests and newer recipient studies. The final verifier is [tests/verify_full_reproduction_artifacts.py](../tests/verify_full_reproduction_artifacts.py). The source/history scan is [tests/audit_public_artifact.py](../tests/audit_public_artifact.py) and [tests/audit_public_history.py](../tests/audit_public_history.py). Archive integrity manifests always identify their run commit and should be kept with the corresponding generated SQL evidence.
