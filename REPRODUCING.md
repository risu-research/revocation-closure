# Reproducing the public experiments

The [v1.0.0 research archive](https://doi.org/10.5281/zenodo.24410799) preserves the fixed inputs, executable evaluation code, expected outcomes and independent audit programs at commit `c1f15fb1146a10cb3690e755bf8aa7deaa23c3a5`. Reproduce the paper's recorded results from this [release tag](https://github.com/risu-research/revocation-closure/releases/tag/v1.0.0). The tests use synthetic material and selected manually reviewed clauses from public court orders.

## One-click full reproduction

Open [Reproduce the full public research artifact](.github/workflows/reproduce-full-artifact.yml) in the GitHub Actions tab and select **Run workflow**. This calls the five specialized checks and executes the remaining checkpoint, HTTP source-read, trusted-custody and independent-recipient modules. Job results and any retained synthetic evidence appear under the new workflow run.

The component workflows remain independently runnable:

- [Complete tracked-file and court-data checks](.github/workflows/audit-public-artifact.yml)
- [Actor and deadline recipient](.github/workflows/verify-actor-clock.yml)
- [Program and signed-output binding](.github/workflows/verify-program-binding.yml)
- [Instrumented document reads and SQL effects](.github/workflows/verify-document-to-effect.yml)
- [Current permission and typed-policy integrity](.github/workflows/verify-policy-integrity.yml)

The final `verify-complete-artifact` job downloads the ten experimental evidence groups from that run. It checks their stored SQL effects and policy-mutation records, scans the evidence for sensitive content, and publishes a `full-reproduction-verification` artifact listing SHA-256 digests for every file. The [public audit description](results/PUBLIC_ARTIFACT_REPRODUCTION_AUDIT.md) maps each group to the corresponding experiment.

To repeat the final verification offline, download all ten evidence groups from **one** full Actions run, preserving each artifact's top-level folder name, then use:

```bash
python tests/verify_full_reproduction_artifacts.py PATH_TO_DOWNLOADED_GROUPS --out verified-manifest.json
```

An Actions run verifies behavior **at its own commit SHA**. Generated signing keys, nonces and temporary service ports differ between runs. The fixed scenario decisions, SQL effects and independent checks are the reproducibility targets.

## Local checks before running experiments

Python 3.12 or newer is sufficient for the standard-library verifiers. Run from the repository root:

```bash
python tests/audit_public_artifact.py
python tests/audit_public_history.py
python tests/verify_recorded_results.py
python tests/verify_public_summaries.py
python experiments/court_coding/verify_public_coding.py
python experiments/court_coding/verify_conditional_coding.py
python -m unittest discover -s tests -p 'test_full_reproduction_integrity.py' -v
```

The static auditor checks tracked text files for credentials and personal paths, Python syntax, internal Markdown links and the 40-order coding reconciliation. The history auditor requires a complete Git checkout and checks older reachable file revisions as well. The court-data tests independently verify the original 520 decisions and the 120 recorded changes. The [source-page follow-up](experiments/court_coding/SOURCE_REVIEW_REPORT_2026-11-20.md) explains the five historical source-check flags, including the four verified page locations and the scoped Voltstar review.

## LangGraph checkpoint and provenance modules

Use Python 3.12 and install the selected LangGraph version:

```bash
python -m pip install 'langgraph==1.2.12'
```

**Court clause fixtures:** run the 25 source-linked clause fixtures and eight checkpoint tests, then verify the recorded summary.

```bash
python experiments/court_policy/legal_order_probe.py
python tests/verify_recorded_results.py
```

**Provenance fault matrix:** 18 defined fault types, two legal contexts, three guards and 20 held-out seeds create 2,160 independent *executions of fixed scenarios*.

```bash
python experiments/provenance_stress/provenance_stress.py --partition holdout
python tests/verify_provenance_evaluation.py provenance_holdout_result.json
```

[Protocol](experiments/provenance_stress/PROTOCOL.md) · [Recorded evaluation](results/provenance_stress_summary.json)

**External HTTP/SQLite effects:** the helper starts a local receiving service, replays 1,152 held-out cases and independently checks the physical SQLite database.

```bash
bash experiments/external_effects/run.sh holdout
```

[Protocol](experiments/external_effects/PROTOCOL.md) · [Original archive SQL re-audit](results/EXTERNAL_EFFECT_SQL_REAUDIT.md) · [Read-only cross-archive verifier](tests/verify_external_effect_archives.py)

**Instrumented source reads:** the source service records HTTP tool reads and runs the 540-case held-out matrix through its own SQL effects ledger.

```bash
bash experiments/observed_tool_reads/run.sh holdout
```

[Protocol](experiments/observed_tool_reads/PROTOCOL.md) · [Recorded evidence](results/OBSERVED_TOOL_READ_EVIDENCE.md)

Both shell helpers require Linux or macOS, Bash, local loopback ports, and SQLite. The produced synthetic outputs stay in their ignored `_runs/holdout/` directories.

## Isolated trusted broker and downstream recipient

Use Linux with Docker, a working network connection to retrieve the published Python image and `langgraph==1.2.12`, and permission to run containers. These two helpers create real Linux user-identity boundaries.

```bash
bash experiments/trusted_custody/run.sh holdout
bash experiments/independent_recipient/run.sh holdout
```

The first performs 168 selected synthetic conditions with source custody, evidence-bound broker operations and an independent SQL audit. The second replays 576 historical checkpoint conditions across four independent-recipient modes, preserving separate owner, agent and recipient roles.

[Trusted custody protocol](experiments/trusted_custody/PROTOCOL.md) · [Trusted custody audit](results/TRUSTED_CUSTODY_EVIDENCE.md)

[Independent-recipient protocol](experiments/independent_recipient/PROTOCOL.md) · [Acknowledgment SQL re-audit](results/RECIPIENT_ACK_SQL_REAUDIT.md)

## Signed program binding and actor-specific clocks

The program-binding module requires a disposable Linux VM/container with Python 3.12+, `libseccomp` and root privileges within that test environment. From the repository root:

```bash
cd experiments/program_binding
python -m pip install -r requirements.txt
PYTHONPATH=. python -m experiments.trusted_transform.run_stage_q --out fresh_baseline
PYTHONPATH=. python tests/independent_stage_q_audit.py . fresh_baseline
PYTHONPATH=. python -m experiments.trusted_transform.run_stage_q --approve-literal --out fresh_ablation
PYTHONPATH=. python tests/independent_stage_q_audit.py . fresh_ablation
python tests/check_expected_metrics.py
cd ../..
```

The two branches compare approved and unapproved program bytes and physically committed SQL effects. [Signed-program audit](results/PROGRAM_BINDING_CI_AUDIT.md).

For the actor-and-clock module, use a disposable Linux environment capable of spawning separate test UIDs:

```bash
cd experiments/actor_clock
python -m pip install 'cryptography==46.0.4'
sha256sum -c SHA256SUMS.txt
python -m unittest discover -s tests -p 'test_*.py' -v
python -m stage_r.run_study --out /tmp/actor_clock_fresh
python tests/independent_audit.py /tmp/actor_clock_fresh
python tests/check_public_reproduction.py /tmp/actor_clock_fresh
cd ../..
```

Run its study as root **inside the disposable environment** if the operating system needs root privileges to allocate the separate worker/recipient identities. [Eight duty inputs](experiments/actor_clock/README.md) · [SQL and original-clause audit](results/ACTOR_CLOCK_SQL_AND_SOURCE_AUDIT.md).

## Document-to-effect writes and typed-policy checks

Use Python 3.13 with local HTTP and SQLite support. In the following commands, install dependencies at the repository root and then run each module in its own directory:

```bash
python -m pip install -r experiments/document_to_effect/requirements.txt
python -m pip install -r experiments/policy_integrity/requirements.txt

(cd experiments/document_to_effect && python tests/reproduce.py)
(cd experiments/policy_integrity && python reproduce.py)
```

The first program checks **46 actual HTTP write attempts** from newly recorded document reads through signed permits to five recipient databases. The second uses the same 46 fixed scenario definitions to compare the original **17** and strengthened **12** committed writes; it also injects 13 typed-policy mutations, testing 12 through actual HTTP/SQLite receiving services.

[Signed document-to-effect evidence](results/DOCUMENT_TO_EFFECT_CHAIN_AUDIT.md) · [Policy integrity and 13 mutations](results/POLICY_INTEGRITY_SQL_REAUDIT.md).

Both modules use fixed synthetic legal-source summaries and generate fresh run-specific signing keys.

## Court-order policy extraction and coding

The lexical transfer experiment uses the standard library to assess held-out legal-policy extraction and exercise its independent HTTP/SQLite effect tester:

```bash
(cd experiments/court_order_transfer && python tests/check_public_reproduction.py)
```

[Source inputs and fixed gold records](experiments/court_order_transfer/README.md) · [Court-order coding dataset and codebook](experiments/court_coding/README.md) · [Source review](experiments/court_coding/SOURCE_REVIEW_REPORT_2026-11-20.md).

## Evidence interpretation and retention

The [cross-experiment evidence map](results/SECTION_VI_CROSS_EXPERIMENT_EVIDENCE_MAP.md) records denominators, original Actions runs and retained physical databases for the eight recipient-related studies. Selected source hashes and verified saved summaries reside in `results/`, and each module's independent auditor reads the stored effects or signed records without relying on an agent's success response.

GitHub retains Actions-generated ZIP archives for a limited period; the links in the evidence reports may eventually expire. Use the current source code and relevant workflow to regenerate fresh synthetic evidence. Keep the run commit SHA, independent audit output, recipient SQL records and fixed input/source manifest together when citing a result. Different runs generate different keys and hashes for random test data, so compare the specified decisions and counts rather than the temporary byte strings.
