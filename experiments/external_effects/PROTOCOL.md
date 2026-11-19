# Independent effect verification

The experiment asks whether an old LangGraph checkpoint can commit a new downstream write after its source is revoked. It separates state replay, a persisted effect, and the independent observer of that effect.

## Three independently executed parts

1. Workflow: external_effect_runner.py runs real LangGraph checkpoints, repairs the latest state, and replays an earlier pre-effect snapshot.
2. Receiver: external_effect_sink.py runs as a separate HTTP process and writes to its own SQLite database. The guarded endpoint checks policy and provenance in the same BEGIN IMMEDIATE transaction as the write. An intentionally unguarded endpoint models a vulnerable downstream interface.
3. Observer: external_effect_auditor.py runs separately and reads the database in SQLite read-only mode. It verifies physical rows, their exact payload, policy epochs, unique case IDs and the oracle source lineage in a manifest frozen before execution. It never accepts a successful return value as proof that data were persisted.

The experiment employs a localhost service on the same test VM. This service is a synthetic external-effect receiver, not a commercial cloud or legal service.

## Frozen test matrix

- 16 source-provenance and authorization-timing scenarios.
- Three guards named cached, client_precheck and sink_atomic.
- Two manually specified legal-policy fixtures, corresponding to Acosta producer notice and NECEC pending challenge.
- Development seeds 901, 902, 903 and 904.
- Held-out seeds 7001 through 7012.
- 384 development and 1,152 held-out real historical checkpoint replays.

Each seed varies opaque synthetic payload identity. It does not create new independent cases or distinct error-generating processes.

The policy-visible case key and payload do not encode source truth. True source dependency is withheld in the oracle manifest. The receiver receives only declared synthetic read receipts. The experiment checks valid, omitted, stale, incomplete and falsely complete receipts. A complete-but-false record is a deliberately unresolvable information problem.

## Guard comparison

| Mode | Authorization boundary | Effect operation |
| --- | --- | --- |
| Cached | Boolean approval saved before the notice, simulated in the checkpoint | Insecure unguarded HTTP write |
| Client precheck | Query current policy just before writing; a policy transition can then intervene | Insecure unguarded HTTP write |
| Sink atomic | Evaluate current policy and receipt within the same SQL transaction as the write | Server-side guarded HTTP write |

The server deliberately exposes an insecure endpoint for the first two negative controls. A system adopting the guarded operation must prevent clients from bypassing it.

## Independent readback and outcomes

The external observer opens SQLite in read-only mode. It reconstructs policy at the epoch recorded with each committed write, verifies payloads and duplicate prevention, then classifies the row using the synthetic ground-truth dependency held separately from the receiver.

- Unauthorized persisted write: a new row using revoked source R committed while R was revoked.
- Clean effect preserved: an allowed new row using only independent source K.
- Race violation: policy was checked before revocation but the effect was committed after it.
- Unresolved: a guard could not authorize with missing, incomplete or mismatching receipt evidence.

The receiver is stopped before the readback audit. The Actions workflow checkpoints the SQLite WAL into the database file, switches to DELETE journal mode and verifies SQL integrity. This matters because an earlier superseded archive omitted WAL-resident rows. The final archives contain all rows, independently rechecked from the downloaded ZIP files.

## Held-out results

Each guard receives 384 evaluations, including 216 revoked-derived cases at effect time and 120 genuinely clean cases. The remaining 48 per guard are valid authorization or revocation-withdrawal controls.

| Guard | Unauthorized writes out of 216 | Clean effects retained out of 120 | Unauthorized race writes out of 48 | Abstentions |
| --- | ---: | ---: | ---: | ---: |
| Cached | 216 | 120 | 48 | 0 |
| Client precheck | 96 | 48 | 48 | 120 |
| Sink atomic | 48 | 48 | 0 | 120 |

The remaining unsafe writes under sink atomic come from deliberately falsely complete provenance, including a mixed-source derivation whose revoked source was omitted. The independent observer detects them after the fact, but cannot undo those already committed writes.

All rates are conditional on an equally weighted, constructed fault matrix. They are neither field failure-rate estimates nor estimates of effectiveness across independent deployments.

## Reproduce

Install Python 3.12 and LangGraph 1.2.12, then run from the public repository root:

    python3 -m pip install 'langgraph==1.2.12'
    bash experiments/external_effects/run.sh dev
    bash experiments/external_effects/run.sh holdout

The runner saves its oracle manifest, external SQLite database, client responses, read-only audit and hashes under experiments/external_effects/_runs. The output location may be overridden by a second positional argument.

Original complete executions:

- [Final development Actions run](https://github.com/risu-research/formal-exec-2609/actions/runs/44457578111)
- [Final held-out Actions run](https://github.com/risu-research/formal-exec-2609/actions/runs/44457583262)
- [Pinned source, summary and evidence hashes](../../results/external_effects_summary.json)

## Scope

This is a constructed policy and fault-injection test using InMemorySaver and a distinct HTTP/SQLite service. An earlier separate experiment tested PostgresSaver with a simpler replay condition. The saved pre-notice approval bit is synthetic. Receipt completeness is asserted rather than externally attested. The guard's success against this race assumes all effectful writes go through the guarded endpoint. No LLM outputs, actual provider deletions or live court claims were executed.

The previously submitted paper remains unchanged. No GitHub release, Zenodo deposition or DOI is created by this experiment.
