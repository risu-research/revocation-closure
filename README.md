# Revocation Closure

Research artifacts for *After the Clawback: Revocation Closure in Agentic Legal Workflows*, accepted at the Tenth Annual Workshop on Applications of Artificial Intelligence in the Legal Industry, co-located with IEEE BigData 2026.

This repository gathers reproducible tests for post-use legal revocation in agent workflows. The first verified module converts cited provisions from four entered federal protective orders into **manually specified policy fixtures** and runs synthetic effect-replay tests using LangGraph 1.2.12.

## Current independently runnable module

- `experiments/court_policy/legal_order_probe.py` — clause-specific policy controls and replay experiments.
- `experiments/court_policy/COURT_ORDER_MAP.md` — docket references, section references, exact scope and interpretation limits.
- `results/court_policy_result.json` — the recorded output from a passing public GitHub Actions run.
- `results/PROVENANCE.md` — fixed commit, runner link and evidence hashes.

Run from the repository root using Python 3.12:

```bash
python -m pip install 'langgraph==1.2.12'
python experiments/court_policy/legal_order_probe.py
```

The script produces `legal_order_result.json` in the current working directory. It asserts 25 fixed policy fixtures and eight historical-checkpoint replay scenarios. It uses synthetic markers and a local SQLite effects ledger. No confidential litigation content, vendor API, or legal filing is processed.

## Provenance fault evaluation

A second, independently reproducible module studies missing, mislabeled, stale and falsely complete source-dependency evidence.

- [Protocol and limitations](experiments/provenance_stress/PROTOCOL.md)
- [Runnable checkpoint experiment](experiments/provenance_stress/provenance_stress.py)
- [Development and held-out evaluation summary](results/provenance_stress_summary.json)
- [Independent output auditor](tests/verify_provenance_evaluation.py)

The evaluation covers 18 fixed fault types, three current-policy guard strategies, two court-policy fixtures and disjoint development and evaluation seeds. The 2,160 held-out synthetic checkpoint replays use LangGraph and an independent SQLite write ledger. Its aggregate results describe deliberately constructed failure conditions and do not estimate their occurrence in production.

Run using Python 3.12:

```bash
python -m pip install 'langgraph==1.2.12'
python experiments/provenance_stress/provenance_stress.py --partition holdout
python tests/verify_provenance_evaluation.py provenance_holdout_result.json
```

The complete per-run result is retained as an [Actions artifact](https://github.com/risu-research/formal-exec-2609/actions/runs/44455344566). The source revision and result hash are pinned in the summary.

## Independent external-effect verification

A third module tests whether historical checkpoint replay creates a **persisted downstream effect** after revocation and whether a separately executed, read-only observer can verify the actual resulting storage state.

- [Method and pre-registered scenarios](experiments/external_effects/PROTOCOL.md)
- [HTTP effect receiver](experiments/external_effects/external_effect_sink.py)
- [Real LangGraph replay driver](experiments/external_effects/external_effect_runner.py)
- [Independent SQL auditor](experiments/external_effects/external_effect_auditor.py)
- [One-command development or held-out rerun](experiments/external_effects/run.sh)
- [Verified result and source hashes](results/external_effects_summary.json)

The held-out run covers 1,152 seeded checkpoint replays across a fixed matrix. It compares cached approval, client-side prechecks, and storage-side checks performed inside the write transaction. An independent observer reads physically persisted SQLite rows and policy event history without relying on the workflow's success messages. The matrix includes revocation between a client check and an external write.

Results describe controlled synthetic conditions, not live legal-service behavior, validated provider deletion, or real-world error frequencies. Incorrectly complete receipts remain a known failure boundary. The work is deliberately separate from the frozen submitted manuscript.

## Evidence boundary

The court orders are cited as public source documents. A human translated selected clauses into test fixtures. Passing tests confirm that the implemented interpreter and replay harness behave as those fixtures specify. They do not certify compliance by any real workflow, law firm, or AI provider. Missing or falsely complete dependency information remains a failure boundary.

Earlier component-level tests using Chroma, Qdrant and PostgreSQL-backed LangGraph are distinct evidence and are not represented as rerun by this module. They are tracked in the research recovery materials.

The source records are linked rather than copied into the repository. Tests and source code are maintained separately from the manuscript's frozen submitted experimental results. The camera-ready artifact scope will be explicitly tagged when the final evaluation is settled.

## License and citation

Original test code is released under MIT in this repository. Referenced court orders and third-party software retain their own terms. A GitHub release or Zenodo DOI will be created only after the author explicitly approves a frozen version.
