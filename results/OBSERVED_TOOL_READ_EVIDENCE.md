# Observed tool reads and nondeterministic replay evidence

## Source and execution

- Public source: [revocation-closure/experiments/observed_tool_reads](https://github.com/risu-research/revocation-closure/tree/main/experiments/observed_tool_reads)
- Calculation branch: `risu-research/formal-exec-2609`, `exec/j-trace824`
- Final unchanged experimental source blob hashes: source service `4981b129a8f7f52be6dacc808007c347c6a14dad`, runner `a484dc6fef339f323025c23acad29b8f8038dc56`, independent auditor `0133a9e70f2d92d47f9534286b2f6c4d1dfe11eb`, run script `62e040f7c07413164119d05439dcd83354d29690`
- [Development run 44460188982](https://github.com/risu-research/formal-exec-2609/actions/runs/44460188982), artifact `14500135632`
- [Held-out run 44460302186](https://github.com/risu-research/formal-exec-2609/actions/runs/44460302186), artifact `14499637105`

| Split | Cases | Source read events | Unique nondeterministic transforms | Physical effects | Distinct clean-source nonce pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 180 | 180 | 180 | 120 | 12 |
| Held-out | 540 | 540 | 540 | 360 | 36 |

## Original artifact SHA-256

| Split | Archive member | SHA-256 |
| --- | --- | --- |
| Development | `evidence.sqlite` | `49f55ac3bb9225c3576343930984e7f62bb6d5ce5171c0b3afb4f90157b10250` |
| Development | `tool_read_dev_audit.json` | `e85e13673070647fbcc705c73983ff560bbc7ed4fa41cab4b2c1554581190b42` |
| Development | `tool_read_dev_oracle.json` | `cb142b75ee9e10eb2f7ed1d77d7df94d1b9980e87c797a02c762b8e9fdc8b739` |
| Held-out | `evidence.sqlite` | `b9ce256fd295be2fb1f762b0f89ba22706af6a736e14ac528e7911b0577001cd` |
| Held-out | `tool_read_holdout_audit.json` | `48308343845dda0cfd07efd128cd4f9bc012797ee441d5689b18514d2f089a6a` |
| Held-out | `tool_read_holdout_oracle.json` | `bd760ac328617610ea6fba1a2e64d7a345c37b8f0642c7601b2b7de4bd6c6d75` |

The original ZIP archives were extracted in a separate container-backed environment after successful Actions runs. The SQLite files passed `PRAGMA integrity_check` and contained 180 and 540 transform rows respectively. The independent Python auditor was rerun against those archived databases and oracle manifests. On a separate disposable copy of the development database, changing one physically stored effect caused the auditor to fail with an assertion.

**Reproductions will not be byte-identical.** Fresh entropy is an intentional property of the transform. The oracle's expected guard decisions, persisted-effect counts and all invariants are stable; the precise transform nonces and resulting archive file hashes vary across reruns.

## Qualified findings

The tool-observed read trace blocks or defers replay when the source-service event log identifies revoked data and the output hash matches the registered transformation. The trace guard can admit correctly tracked clean-source outputs despite genuine nondeterminism.

The deliberately untracked endpoint proves a failure condition. If a revoked source bypasses instrumentation and another clean source is logged, the source-service trace is falsely complete, and the trace guard accepts an unauthorized write.

The output-registration endpoint stores the workflow's reported transform output and nonce. Independent replay checks that it matches the precommitted oracle input values. The service itself has no complete reference monitor for unobserved reads and issues no independently signed evidence of full provenance.

This experiment changes no original accepted paper or historical result. The repository has no new GitHub release, Zenodo archive or DOI associated with this experiment. These steps require explicit author approval.
