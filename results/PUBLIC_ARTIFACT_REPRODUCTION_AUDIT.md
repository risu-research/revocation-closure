# Public Artifact Reproduction and Integrity Audit

The [complete paper-to-artifact evidence index](PAPER_TO_ARTIFACT_COVERAGE.md) maps every manuscript section and all nine tables to its fixed data and executable verifier.

This repository publishes the code, manually reviewed policy fixtures, synthetic evaluation data and independent checks supporting *After the Clawback: Revocation Closure in Agentic Legal Workflows*. The experiments follow distinct test matrices. Each result is tied to a source revision and independently checked receiving-service evidence.

## Versioned source archive

The [Zenodo v1.0.0 record](https://doi.org/10.5281/zenodo.24410799) preserves the public source snapshot corresponding to [GitHub release v1.0.0](https://github.com/risu-research/revocation-closure/releases/tag/v1.0.0) and commit `c1f15fb1146a10cb3690e755bf8aa7deaa23c3a5`. The published Zenodo ZIP is 446,530 bytes (MD5 `fc5ad1efce5670b0b4ab1c77488400e7`). Source files and fixed evaluation inputs are preserved there; GitHub Actions regenerates run-specific SQLite evidence and independent verification manifests.

## Reproduction entry points

- [One-click full public reproduction](../.github/workflows/reproduce-full-artifact.yml)
- [Local reproduction commands](../REPRODUCING.md)
- [Public-file security, code and link audit](../tests/audit_public_artifact.py)
- [Complete public Git history audit](../tests/audit_public_history.py)
- [Independent completed-artifact verifier](../tests/verify_full_reproduction_artifacts.py)
- [Cross-experiment evidence map](SECTION_VI_CROSS_EXPERIMENT_EVIDENCE_MAP.md)

The full workflow runs ten source/data and executable study jobs. A final job downloads every resulting artifact, validates the experiment-produced SHA-256 inventories, checks physical SQLite effects, validates required mutation controls, screens archived files for credentials and personal paths, and records each file's SHA-256 in a commit-bound manifest. Negative-control tests confirm that altered, missing, malformed and out-of-archive hash entries are rejected. A failed prerequisite or inconsistent archived effect prevents that final verification from succeeding.

## Independent test evidence

| Study | Reproduced observation | Physical or independent check |
| --- | --- | --- |
| Court-policy fixtures | 25 legal-policy conditions and eight historical checkpoint cases | Fixture assertions and recorded-result checker |
| Court-order coding | 40 orders, 520 original and 520 conditional cells, 120 recorded revisions | Separate codebook and data-matrix verifiers |
| Provenance stress | 2,160 held-out source-evidence checkpoint replays | Independent seeded-case evaluator |
| External HTTP/SQL effects | 1,152 held-out cases, 720 stored SQL writes | SQLite observer and database integrity |
| Observed HTTP tool reads | 540 cases, 360 committed effects | Read-log and recipient-effect auditor |
| Retrospective source recovery | 180 development and 540 held-out trace reanalyses | Archived original read/SQL evidence, six-candidate source reconstruction, fresh independent validation |
| Component deletion and history | Five original component studies, 3 of 4 historical checkpoints retaining a revoked marker | Original Git blobs, result records and fresh Chroma/Qdrant/Haystack/LlamaIndex/LangGraph runs |
| Two saver checkpoint effects | 7 InMemorySaver and 7 PostgresSaver original scenarios | Saved SQL rows, two independently rerun checkpoint-to-write tests |
| Trusted custody | 168 fixed conditions, 60 committed effects | Isolated Linux identities and read-only SQL observer |
| Independent recipient | 576 checkpoint replays, 396 committed effects | Owner/recipient acknowledgment auditor |
| Program binding | Four baseline writes and five approved-literal control writes | Signed source/program/output and physical SQL audit |
| Actor-specific clocks | 17 write attempts, five committed effects | Signed actor/event records and legal-clock checks |
| Document-to-effect chain | 46 requests, 17 physical effects in each of two fresh runs | 18 source reads, 38 permits and recipient SQL |
| Policy integrity | Paired 46 requests with 17 baseline and 12 strengthened writes in each of two runs | Five changed decisions, 13 policy defects and 12 HTTP mutation pairs |
| Court-order policy transfer | Fixed lexical extraction and selected recipient-effect cases | Sealed source/gold and effect verification |

The row totals come from different designed synthetic case families. Policy integrity reuses the document-to-effect scenarios. Two repeated runs within a module check repeatability with fresh credentials. Each denominator must remain attached to its experiment.

## Public-source and privacy checks

The public tree is scanned for credential files, signing-key material, access tokens, personal email addresses, local user paths, Python syntax errors and broken relative links. The history audit checks every reachable named Git blob in a complete checkout, including superseded file versions. Both checks report rule IDs and affected paths without printing potential secret values.

Full reproduction also checks generated artifacts before accepting the final evidence manifest. The sixteen uploaded evidence groups contain synthetic SQLite effects, public verification keys, independent audit outputs and SHA-256 records. Test signing credentials are generated for the experiment and remain ephemeral.

## Source scope and evidence retention

The entered court orders are linked to public legal records. The execution tests use short locally frozen excerpts, manually interpreted policy fields and invented discovery sources. Reruns work without downloading live litigation materials. Structural-policy tests compare against those fixed legal fields, and separate controls cover incorrect dependency claims and undelivered notices.

The original development and held-out tool-read evidence for retrospective recovery is preserved in base64-encoded text archives in source control. The early component results and original checkpoint-effect SQL rows are preserved as small JSON records with their original source Git object hashes. GitHub Actions ZIP archives for the other studies have a limited retention period. Source code, fixed data, expected results and independent audit programs remain accessible at the referenced Git commit. A fresh workflow run regenerates the evidence. Keep the commit SHA, independent audit output and physical SQLite effects together when citing a result. Random signing keys and identifiers change between runs, so decision and effect checks take priority over byte-identical temporary credentials.

This public artifact contains the reusable research code and test records. Manuscript working files, private handoffs and administrative records remain outside the repository.
