# Provenance stress test evidence

## Pinned source and executions

- Compute repository: [formal-exec-2609](https://github.com/risu-research/formal-exec-2609)
- Experimental branch: `exec/j-pv631a`
- Final experimental source commit: [ddded3472e7e1183162407322fca475afcb2164a](https://github.com/risu-research/formal-exec-2609/commit/ddded3472e7e1183162407322fca475afcb2164a)
- Public source blob SHA-1: `18ec60f938dbba6fb8dd4f9ccfb8ff9ed74a9dd4`
- Source SHA-256: `f4d825d9a9c3c112c85e5547c9fd964abfbbb0dbb2ca28ca15d02d8638818cb0`
- Environment: Python 3.12 and LangGraph 1.2.12, with real LangGraph checkpoint replay and SQLite effect writes

## Original completed runs

| Split | Executed run | Full recorded result | Result SHA-256 |
| --- | --- | --- | --- |
| Development, four seeds | [#44455269658](https://github.com/risu-research/formal-exec-2609/actions/runs/44455269658) | [Original Actions archive](https://github.com/risu-research/formal-exec-2609/actions/runs/44455269658/artifacts/14496729744) | `bb020eb3c5989e5dde3d7d7fa0c719c2c5e9015bea0b0a7657f6bdeaee0ff180` |
| Held-out, twenty seeds | [#44455344566](https://github.com/risu-research/formal-exec-2609/actions/runs/44455344566) | [Original Actions archive](https://github.com/risu-research/formal-exec-2609/actions/runs/44455344566/artifacts/14497580903) | `cfcfd5480c5c422d54f8d73d3651957da209d7d7705a22e87d09165ecf877d50` |

The recorded development and held-out results have the same execution-source SHA-256. The source was revised once after an initial developmental audit to make the observable collision pair share the same policy-facing artifact identifier. Both final splits use that revised source. Earlier superseded Actions runs remain in the compute repository history but are not used in the reported table.

## Independent output audit

A separate public verifier was checked out at pinned public artifact commit `6829300ddef64dc7fe16e5a226fd706c05adc772`. The verifier downloaded both original Actions evidence archives and checked the exact result SHA-256, each row's oracle/effect accounting, the aggregate metrics and the collision-pair invariants.

- Independent audit [run #44455997894](https://github.com/risu-research/formal-exec-2609/actions/runs/44455997894)
- Audit [result archive](https://github.com/risu-research/formal-exec-2609/actions/runs/44455997894/artifacts/14497811882)
- Development audit: **432 checks passed**, including 24 collision-pair comparisons
- Held-out audit: **2,160 checks passed**, including 120 collision-pair comparisons

## Reproducibility and interpretation

Run the [public source](../experiments/provenance_stress/provenance_stress.py) and validate outputs with the [auditor](../tests/verify_provenance_evaluation.py). The summary JSON is stored in [provenance_stress_summary.json](provenance_stress_summary.json).

The experiments are deterministic, seeded fault injections. Every occurrence of a fault template receives equal weight. The numbers therefore describe test coverage and known failure modes rather than field failure rates, algorithm superiority on independent deployments or prevalence in actual litigation.

The `receipt` method depends on a simulated independent read-event record. When that record's completeness assertion is itself false, the experiment deliberately shows unsafe acceptance. No cryptographic receipt validation or independent third-party provider compliance has been tested.

No GitHub release, Zenodo deposit or DOI has been created for these results. A release remains subject to explicit author approval.
