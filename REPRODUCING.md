# Reproduce the experiments

Run the commands from the repository root. Each module contains its protocol, source code, fixed synthetic scenarios and an independent output check. The result summaries under `results/` record the original evaluations.

## Recorded results

First check the published summaries with Python 3.11+.

```bash
python tests/verify_recorded_results.py
python tests/verify_public_summaries.py
```

These checks inspect saved result files. The commands below rerun the actual experiments.

## Court-order policy fixtures

Requires Python 3.12 and LangGraph 1.2.12.

```bash
python -m pip install 'langgraph==1.2.12'
python experiments/court_policy/legal_order_probe.py
python tests/verify_recorded_results.py
```

Expected output is 25 fixed clause tests and eight historical-checkpoint replay tests. The court references and clause mapping are in [COURT_ORDER_MAP.md](experiments/court_policy/COURT_ORDER_MAP.md).

## Provenance fault evaluation

```bash
python experiments/provenance_stress/provenance_stress.py --partition holdout
python tests/verify_provenance_evaluation.py provenance_holdout_result.json
```

The evaluation has 2,160 checkpoint replays. The recorded counts for unauthorized effects are 400, 160 and 80 across cached approval, checkpoint metadata and separate source receipts.

## External-effect receiver

Requires Linux or macOS with Bash, local HTTP ports and SQLite.

```bash
bash experiments/external_effects/run.sh holdout
```

The script launches the receiver, resumes historical checkpoints and audits its persisted SQL rows. The 1,152-case result uses 16 templates, two legal-policy fixtures, 12 held-out seeds and three guards.

## Observed tool reads

```bash
bash experiments/observed_tool_reads/run.sh holdout
```

The script starts the source service, records actual tool reads and checks the resulting SQL effects. The fixed held-out matrix has 540 executions.

## Trusted source custody

Requires Linux with Docker. The test creates separate process identities and runs inside a disposable container.

```bash
bash experiments/trusted_custody/run.sh holdout
```

The auditor checks the resulting SQLite ledger against the held-out oracle. The recorded evaluation contains 168 conditions.

## Independent recipient authorization

Requires Linux with Docker.

```bash
bash experiments/independent_recipient/run.sh holdout
```

The recipient keeps its own policy and SQLite effect ledger. The evaluation contains 576 historical-checkpoint replays across four recipient modes. The protocol records missed-notice and false-clean-issuance controls.

## Document-to-effect replay

Requires Python 3.13 and `cryptography==46.0.4`, with local HTTP and SQLite support.

```bash
python -m pip install -r experiments/document_to_effect/requirements.txt
cd experiments/document_to_effect
python tests/reproduce.py
```

The test replays 46 synthetic write attempts through a separate HTTP/SQLite recipient, checks 17 persisted writes and nine unsafe control outcomes, and reconstructs the decisions in a read-only SQL audit. For the saved request and database evidence, see [the module instructions](experiments/document_to_effect/README.md).

## Inputs and evidence

Every experiment uses synthetic source records and researcher-specified legal-policy fixtures. The original result JSON, source revisions, independent audit procedures and GitHub Actions records are linked from the [results directory](results/). Repeated seeds vary synthetic identifiers within fixed scenario families.

Keep source code, audit code and result files together when comparing a new run with the recorded evaluation.
