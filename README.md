# Revocation Closure

Reproducible research artifacts for *After the Clawback: Revocation Closure in Agentic Legal Workflows*, accepted for the AI in the Legal Industry workshop at IEEE BigData 2026.

Legal clawback obligations can change after an agent has saved a checkpoint, read source material or received permission to create an effect. These experiments connect a selected legal-policy record, the sources and programs contributing to an output, the receiving service's current authorization, and the record of a committed write.

**[Reproduce the experiments](REPRODUCING.md)** · **[Full artifact and privacy audit](results/PUBLIC_ARTIFACT_REPRODUCTION_AUDIT.md)** · **[Cross-experiment evidence](results/SECTION_VI_CROSS_EXPERIMENT_EVIDENCE_MAP.md)** · **[Run the full Actions evaluation](.github/workflows/reproduce-full-artifact.yml)**

## Research components

The studies have different scenario matrices. Their counts should be interpreted within each module, with the original expected results and independent auditors linked below.

| Study | Fixed evaluation and primary question | Code and source records | Audited evidence |
| --- | --- | --- | --- |
| Court-order coding | 40 entered orders, 13 codes, 520 decisions, and 120 recorded revisions | [Coding dataset](experiments/court_coding/README.md) | [Reconciliation methods](experiments/court_coding/CONDITIONAL_CODING.md) |
| Clause-policy fixtures | 25 clause checks and eight checkpoint tests | [Policy probe](experiments/court_policy/legal_order_probe.py) | [Recorded evidence](results/PROVENANCE.md) |
| Provenance faults | 2,160 held-out replays; absent or incorrect contributing-source records | [Protocol](experiments/provenance_stress/PROTOCOL.md) | [Audit](results/PROVENANCE_STRESS_EVIDENCE.md) |
| External effect race | 1,152 held-out replays; checks before or within a downstream SQL transaction | [Protocol](experiments/external_effects/PROTOCOL.md) | [Physical SQL re-audit](results/EXTERNAL_EFFECT_SQL_REAUDIT.md) |
| Observed tool reads | 540 held-out executions; actual source reads and transformed outputs | [Protocol](experiments/observed_tool_reads/PROTOCOL.md) | [Audit](results/OBSERVED_TOOL_READ_EVIDENCE.md) |
| Trusted source custody | 168 held-out conditions; isolated source custody and write-time evidence | [Protocol](experiments/trusted_custody/PROTOCOL.md) | [SQL audit](results/TRUSTED_CUSTODY_EVIDENCE.md) |
| Program binding | 17 signed program/effect attempts; authorized versus unapproved code paths | [Module](experiments/program_binding/README.md) | [Fresh-run audit](results/PROGRAM_BINDING_CI_AUDIT.md) |
| Independent recipient | 576 checkpoint replays; owner revocation versus recipient acknowledgment | [Protocol](experiments/independent_recipient/PROTOCOL.md) | [Recipient SQL audit](results/RECIPIENT_ACK_SQL_REAUDIT.md) |
| Actor and clock | 17 write attempts and separate legal-event/deadline tests | [Module](experiments/actor_clock/README.md) | [Source and SQL audit](results/ACTOR_CLOCK_SQL_AND_SOURCE_AUDIT.md) |
| Document to effect | 46 requests, 18 instrumented reads and 38 issued permits | [Module](experiments/document_to_effect/README.md) | [Signed-chain audit](results/DOCUMENT_TO_EFFECT_CHAIN_AUDIT.md) |
| Current permission and policy integrity | Paired 46-case comparison, 17 to 12 writes, 13 structural mutations | [Module](experiments/policy_integrity/README.md) | [Policy SQL audit](results/POLICY_INTEGRITY_SQL_REAUDIT.md) |
| Court-order transfer | Fixed policy extraction and a separate recipient-effect study | [Module](experiments/court_order_transfer/README.md) | [Reproduction tests](experiments/court_order_transfer/tests/check_public_reproduction.py) |

## Start with independently checked records

From the repository root, Python 3.12 or later runs the standard-library-only integrity checks:

```bash
python tests/audit_public_artifact.py
python tests/verify_recorded_results.py
python tests/verify_public_summaries.py
python experiments/court_coding/verify_public_coding.py
python experiments/court_coding/verify_conditional_coding.py
```

These checks verify public file hygiene, relative links, source syntax, selected court-data reconciliation and recorded result summaries. **Fresh executions** are separate: follow [REPRODUCING.md](REPRODUCING.md), or start the [full public reproduction workflow](.github/workflows/reproduce-full-artifact.yml) in the Actions tab. Each experiment keeps its own inputs, test cases and independent auditor. When available, its associated Actions archive contains physical SQL effects or signed evidence.

## What the evidence means

The source references are entered public court orders. The policy interpretations, simulated source records, signatures, agent actions and receiving services are reproducible research fixtures. Their fixed scenario counts measure the specified conditions and distinguish correct-source controls, missed notices, unobserved dependencies and incorrect authorization evidence.

The original court order, the manually reviewed policy representation and the software's final decision are separate forms of evidence. A successful verifier establishes behavior under its recorded input and receiving-service assumptions. The comparison of 17 and 12 writes reuses the same 46 designed scenarios, with newly generated run-specific credentials.

The machine-readable summaries, source-code checks and documented commands remain in this repository. GitHub Actions artifacts have a limited retention period and can be regenerated by running the workflows. New signatures and synthetic nonces naturally differ across executions; reproduce the expected decisions, actual SQL effects and independent checks, not byte-for-byte copies of ephemeral keys.

## Use and citation

Cite the paper title and the repository URL together with the commit SHA used for an evaluation. The code is licensed under [MIT](LICENSE). Public court records and referenced software retain their original rights and terms. This repository contains synthetic test data and public source citations, with no client litigation files or production credentials.
