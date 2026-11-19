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

## Evidence boundary

The court orders are cited as public source documents. A human translated selected clauses into test fixtures. Passing tests confirm that the implemented interpreter and replay harness behave as those fixtures specify. They do not certify compliance by any real workflow, law firm, or AI provider. Missing or falsely complete dependency information remains a failure boundary.

Earlier component-level tests using Chroma, Qdrant and PostgreSQL-backed LangGraph are distinct evidence and are not represented as rerun by this module. They are tracked in the research recovery materials.

The source records are linked rather than copied into the repository. Tests and source code are maintained separately from the manuscript's frozen submitted experimental results. The camera-ready artifact scope will be explicitly tagged when the final evaluation is settled.

## License and citation

Original test code is released under MIT in this repository. Referenced court orders and third-party software retain their own terms. Formal archival release and Zenodo DOI will follow a frozen, independently verified artifact version.
