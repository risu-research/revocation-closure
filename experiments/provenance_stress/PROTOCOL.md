# Provenance fault evaluation

## Research question

When a legal clawback applies to a source that a workflow previously used, how does the fidelity of stored source provenance affect a historical checkpoint's ability to perform a new downstream write?

The evaluation isolates the behavior of authorization checks at a concrete SQLite write boundary. It uses synthetic source labels and saved LangGraph checkpoints. Earlier court-order mapping supplies two fixed policy states. Acosta is represented by an active notice and NECEC by a pending challenge. This is a test of software behavior under selected legal conditions, not an automated reading of either order.

## Pre-specified protocol

The exact tested source is pinned in [the verification summary](../../results/provenance_stress_summary.json).

- 18 predeclared provenance fault templates.
- Three guard strategies, two fixed court-policy states, four development seeds and twenty separate evaluation seeds.
- One real LangGraph checkpoint history and a SQLite write-effects ledger for every case and guard.
- 432 development executions and 2,160 held-out seeded executions.
- An explicit expected-decision matrix inside the source, fixed before the final evaluation.
- Identical software source SHA-256 for the final development and held-out evaluations.

The seeds vary synthetic payload identities. The 18 fault templates repeat for each seed. The aggregate rates are conditional on this constructed fault matrix, and cannot estimate frequencies in deployed systems. The individual executions are repeated controls, not independent legal cases or independent populations. No confidence intervals are computed from those repeated rows.

## Three guards

1. **Cached**. Trusts the approval saved before the notice or challenge.
2. **Embedded**. Rechecks the currently applicable revocation status using dependency labels carried inside the checkpoint. Missing or invalid labels yield an unresolved decision.
3. **Receipt**. Queries a separate SQLite table of synthetic source-read receipts. The receipt has source identifiers, a purported completeness flag and a digest bound to the output. Missing, incomplete and mismatched records yield an unresolved decision. The same current policy is then applied to the stated sources.

The receipt is a **simulated instrumentation record**, stored separately from LangGraph state. Its completeness flag has no external attestation and its digest is not a digital signature. Tests intentionally include receipts that falsely claim to be complete.

## What was injected

- Correct single-source and mixed-source lineage.
- Missing checkpoint dependencies.
- A revoked source mislabeled as clean and a clean source mislabeled as revoked.
- A missing revoked member in a mixed derivation.
- Missing independent receipts.
- Receipts declaring incomplete coverage.
- Old receipts whose payload digest no longer matches.
- Receipts claiming complete coverage with incorrect source membership.
- A paired observable collision whose payload, checkpoint declaration, receipt, artifact identifier, current policy and saved approval are identical, although withheld ground-truth lineage differs.

The collision pair is an important limit on any method confined to the same evidence. A deterministic decision function receives identical observable inputs for the two cases and therefore returns the same answer. Allowing both causes an unauthorized write in the revoked world. Rejecting both discards permissible work in the clean world. An additional trusted observation is required to distinguish the two worlds.

## Outcome measures

- **Unauthorized effects** count new SQL writes whose synthetic oracle lineage includes revoked source `R` after the legal-policy change.
- **Clean work preserved** counts allowed new SQL writes whose oracle lineage consists only of clean source `K`.
- **Unresolved** counts runs postponed because declared provenance or external receipts cannot support a decision.
- The oracle truth is read by the auditor after execution, never by the guards.
- A repaired latest LangGraph state and the retained historical checkpoint are both verified before replay.

## Held-out results

Each guard has 720 evaluations, including 400 intentionally revoked or mixed-source examples and 320 clean examples.

| Guard | Unauthorized writes among 400 affected | Permitted writes among 320 clean | Unresolved among affected | Unresolved among clean |
| --- | ---: | ---: | ---: | ---: |
| Cached | 400 | 320 | 0 | 0 |
| Embedded | 160 | 240 | 40 | 40 |
| Receipt | 80 | 160 | 120 | 120 |

These are **fixture-weighted counts**, not effectiveness or error rates for the legal software population. The receipt guard improves rejection of wrong checkpoint labels when its read receipts are correct. It also abstains more often when receipt integrity is uncertain. When receipts falsely claim complete provenance, it admits the unsafe case and may reject an otherwise clean one.

The clean/unsafe indistinguishability pair is deliberately assigned exactly the same policy-visible ID and evidence. The external oracle classifies the pair differently, and all three guards necessarily make the same decision within that pair.

## Reproduce

Using Python 3.12:

```bash
python -m pip install 'langgraph==1.2.12'
python experiments/provenance_stress/provenance_stress.py --partition plan
python experiments/provenance_stress/provenance_stress.py --partition dev
python experiments/provenance_stress/provenance_stress.py --partition holdout
python tests/verify_provenance_evaluation.py provenance_holdout_result.json
```

The source writes `provenance_dev_result.json` or `provenance_holdout_result.json` in the current working directory. These files contain all individual observations and can be checked against the pinned SHA-256 for the reference evaluation if the same environment and runner behavior produce byte-for-byte deterministic output.

- Development [Actions run 44455269658](https://github.com/risu-research/formal-exec-2609/actions/runs/44455269658)
- Held-out [Actions run 44455344566](https://github.com/risu-research/formal-exec-2609/actions/runs/44455344566)

The full per-execution results are retained as GitHub Actions artifacts and also in the research handoff package. The GitHub repository stores a compact independently checked summary.

## Scope

The experiment demonstrates a reproducible **failure boundary under falsified completeness** and the resulting safety/utility tradeoff. It does not measure the prevalence of such faults, certify third-party provenance collectors, provide adversarial cryptographic guarantees, reproduce nondeterministic LLM output, or test real attorneys' workflows. The LangGraph checkpointer in this experiment is `InMemorySaver`; a separate prior experiment tested `PostgresSaver` with the simpler checkpoint-to-effect scenario.

The submitted manuscript remains frozen. No Zenodo version, DOI or GitHub release has been created for this experiment.
