# Tool-observed provenance with nondeterministic transformations

This experiment follows the controlled [external-effect study](../external_effects/PROTOCOL.md). It replaces manually populated source-read receipts with **real LangChain tool calls to a separate HTTP source service**. The source service creates read-event IDs and writes them to SQLite when a call actually occurs. Synthetic source records are used so the experiment carries no litigation data.

## Research question

Can a workflow verify the provenance of a nondeterministic result at the point of a later external write after a clawback, even if the output differs from an independently rerun transformation? What happens when a read is omitted from the event log or a transformation binding is altered?

The source contains synthetic labels R (revoked upon notice) and K (independent clean information). The two fixed policy states correspond to the previously documented Acosta producer-notice and NECEC pending-challenge examples. They are controlled policy fixtures, not an interpretation or execution of every obligation in the court orders.

## Execution and evidence boundaries

1. **Read.** A LangChain `@tool` function calls an HTTP source service. The service returns actual source content, and its instrumented endpoint creates an immutable-in-this-test read event before returning. Its intentionally untracked endpoint demonstrates bypass risk.
2. **Transform.** A real LangGraph node computes SHA-256 over the ordered content it actually read plus a fresh `secrets.token_hex(16)` nonce. The result differs across otherwise identical clean reads. The node registers the resulting output hash and nonce with the service.
3. **Checkpoint.** LangGraph `InMemorySaver` stores the completed read and transform state. The current state is then repaired. A previous checkpoint immediately before the effect is subsequently resumed.
4. **Effect.** The separate HTTP/SQLite service checks the chosen guard against the current policy and commits or refuses a new SQL row.
5. **Independent audit.** After the service stops, a separate Python program opens its database read-only. Using a withheld oracle manifest and the stored nonce, it recomputes each transform, checks the observed tool reads, reads physical effect rows and reconstructs the policy epoch when each write occurred.

The auditor verifies the service's own read-event log and the transformation content independently. The guard receives the transaction's flow ID, output and transform ID, but never the oracle's actual contributing sources.

**Critical boundary.** The source server can log only those reads made through its instrumented endpoint. A registration stating that an output was derived from the observed events does not certify that there were no additional unobserved reads. This is deliberately tested.

## Fixed matrix

- Fifteen predeclared scenarios: clean/revoked/mixed reads, incorrect or missing checkpoint declarations, uninstrumented reads, partially bypassed reads, altered outputs, stale transform bindings, a released revocation and a same-source nondeterministic pair.
- Three guard strategies.
- Two fixed legal-policy conditions.
- Development seeds 71–72, evaluation seeds 6101–6106.
- 180 development and 540 held-out actual historical checkpoint replays.

The code and audit protocol are identical between development and held-out splits. Each seed creates fresh opaque flow identifiers and nondeterministic outputs; it is not an independent collection of real-world legal cases.

### Guard comparison

| Guard | What it trusts |
| --- | --- |
| Cached | A pre-notice approval bit retained by the old checkpoint |
| Declared | Source labels declared in the checkpoint and the current source policy |
| Tool trace | Read events actually logged at the source service, an output-to-transform hash binding, and the current source policy |

A missing, stale, or mismatched transform record results in `UNRESOLVED` under the tool-trace strategy. Uninstrumented reads can cause either safe abstention when no observed read exists or an unsafe false-clean decision when a separate clean read was recorded.

## Held-out results

Each guard is evaluated on 180 synthetic scenarios, including 84 revoked-source cases under an active restriction, 84 clean-source cases and 12 released-source cases.

| Guard | Unauthorized persisted revoked-source writes | Genuine clean effects retained | Unresolved | Tampered output writes |
| --- | ---: | ---: | ---: | ---: |
| Cached | 84 / 84 | 72 / 84 | 0 | 12 |
| Declared | 36 / 84 | 48 / 84 | 24 | 12 |
| Tool trace | **12 / 84** | 48 / 84 | 48 | **0** |

The remaining 12 prohibited writes under the tool-trace guard come from intentionally bypassed source reads. The instrumented gateway observed a clean K read but missed an additional revoked R read, producing a falsely complete trace.

The observer also verified **36 matched pairs** that consumed identical clean source content but produced distinct outputs due to fresh random nonces. Their source-read traces remained valid, and the trace guard admitted the authorized clean effects. This shows the benefit of retaining provenance of *which inputs were read* instead of demanding byte equality between separate nondeterministic executions.

## Reproduce

Use Python 3.12 and LangGraph 1.2.12, whose transitive dependency supplies `langchain-core`. From the repository root:

```bash
python3 -m pip install 'langgraph==1.2.12'
bash experiments/observed_tool_reads/run.sh dev
bash experiments/observed_tool_reads/run.sh holdout
```

The script starts the external service on localhost port 8778, invokes real tools through LangGraph, finalizes the SQLite WAL to a standalone database file, and invokes the independent read-only auditor. Results appear under `experiments/observed_tool_reads/_runs/<partition>/`. Port can be changed by setting `REVOCATION_SOURCE_PORT` and the output location by supplying the script's second argument.

- [Source and result evidence summary](../../results/tool_read_nondeterminism_summary.json)
- [Successful development run](https://github.com/risu-research/formal-exec-2609/actions/runs/44460188982)
- [Successful held-out run](https://github.com/risu-research/formal-exec-2609/actions/runs/44460302186)

The original complete read-event logs, nonce-bearing transform registrations, oracle manifests, checkpoint execution acknowledgements and final SQL database are preserved in the linked Actions artifacts.

## Scope and scientific interpretation

The test uses real tool invocations, a real external process, a real SQL effect and genuine nondeterministic computation. The underlying records, legal-policy inputs and failure modes are constructed. An output hash is registered by the workflow, so the service has not independently proven the transform's true computational dependence. A compulsory, independently trusted read boundary would be needed to eliminate the bypass tested here.

The reported counts are conditional stress-test results from fixed scenarios, not prevalence estimates, estimates of generalized algorithm superiority, or compliance guarantees. This experiment uses LangGraph InMemorySaver, with PostgresSaver separately examined in an earlier replay test. No live LLM, third-party vendor, production matter or real revocation event is involved.

The accepted manuscript is unchanged. No GitHub release, Zenodo deposit or DOI is created by this experiment. A future archival release requires explicit author approval.
