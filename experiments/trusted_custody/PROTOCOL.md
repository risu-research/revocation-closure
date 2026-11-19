# Trusted custody and evidence-insufficiency evaluation

This module extends the earlier [tool-read trace experiment](../observed_tool_reads/PROTOCOL.md) and the [retrospective candidate-replay pilot](../../results/OBSERVED_TOOL_READ_EVIDENCE.md). It evaluates two linked requirements in a constructed legal-agent workflow:

1. A trusted process has exclusive access to protected source bytes and registers the actual reads used in a transformation.
2. At a later historical checkpoint replay, a protected write requires a valid source-bound certificate and authorization under the **current** policy. Missing or contradictory evidence leads to an unresolved decision.

The software implements a narrow reference-monitor pattern. This design is consistent with OWASP's deny-by-default and server-side access-enforcement guidance. It is not a claim of a newly invented cryptographic primitive.

## Execution boundary

The experiment uses real Linux user identities in an isolated GitHub Actions container.

| Process | Linux user | Can open protected source bytes | Can read signing and admin keys | Can write effect ledger |
| --- | --- | --- | --- | --- |
| Test orchestrator | root | Yes, for test setup | Yes | Yes, for final audit |
| Trusted broker | UID 12001 | Yes | Yes | Yes |
| Untrusted LangGraph worker | UID 12002 | **No** | **No** | **No** |

The raw source files, key files and internal SQLite data live in a 0700 broker-only directory. Source files and signing keys have 0400 access modes. The worker's attempts to open all four restricted resources are tested directly in its own operating-system process. A missing credential cannot be recovered from the worker's environment because the trusted broker receives the key through a private file.

Each source snapshot contains 48 random synthetic bytes generated at runtime. Source bytes are not embedded in the public code or returned to the worker. The broker returns only a nondeterministic digest of the actual input bytes and a signed source-dependency certificate. The HMAC binds flow identifier, issue ID, output digest and source list. The broker also retains the independently recorded issue row and individual read events.

The broker's effect endpoint verifies the signature, the persisted issue record, all read events, the output digest and the **current** source-policy state in one SQLite `BEGIN IMMEDIATE` transaction. It refuses duplicate effects. A separate test controller changes legal-policy states using an admin secret unavailable to the worker.

## Checkpoint experiment

LangGraph 1.2.12 creates a historical checkpoint immediately before an effect. The current thread state is repaired, then the saved checkpoint is resumed after the source-policy change. An untrusted worker attempts effects through a real LangChain `@tool` wrapper. The broker is a separate HTTP and SQLite service.

The fixed protocol includes 14 scenarios per policy, using two manually entered policy states:

- Acosta producer notice.
- NECEC pending privilege challenge.

Both are **policy fixtures** from the earlier court-order mapping. They do not claim to encode every judicial duty or deadline.

Cases include revoked-source replay, mixed-source derivation, clean-source preservation, forged clean provenance, altered output, missing certificate, cross-flow misuse, deleted issue evidence, deleted read evidence, duplicate effects, release of restrictions and direct post-revocation read denial.

The testing service offers a deliberately privileged, **admin-authenticated** fault-injection operation to remove issue or read evidence. The untrusted worker cannot call it. In a real deployment, the corresponding outcomes might arise from retention loss, corruption or independent failures rather than a test controller.

## Development and held-out evaluation

| Split | Seeds | Scenario executions | Physical SQL effects |
| --- | --- | ---: | ---: |
| Development | 31–32 | 56 | 20 |
| Held-out | 5301–5306 | 168 | 60 |

The same four source files were used without modification in both final splits. Held-out runs enforce the source file Git blob hashes before execution.

In the held-out split:

- **Zero unauthorized protected SQL writes** occurred from R-derived work after revocation.
- All **36 valid clean-source effect cases** completed successfully. The larger denominator of 96 clean-source cases includes deliberately invalid or missing-evidence negative controls.
- **72 cases with missing or altered proof** resulted in `UNRESOLVED`, with no new SQL effect.
- **12 post-revocation attempts to derive from R** were blocked before issuance.
- **12 duplicate effect attempts** were blocked on their second submission.
- The 60 allowed effects include permitted clean-source effects, permitted pre-notice R use, and R use after the separately modeled release event.

The independent auditor opens the archived SQLite database read-only, reconstructs the policy epoch at each stored effect, verifies evidence rows and compares with a separate oracle source manifest. It also checks the archived database's integrity and event hashes. After the held-out run, a disposable copy of the SQL effects table was altered. The auditor raised an error as expected.

The raw Actions archives were downloaded again into a separate environment and independently audited. The archived output JSON matched the recomputed audit exactly.

## Retrospective uncertainty is kept distinct from authorization

The independent audit also exercises bounded candidate replay using the saved transform nonce and source snapshots. The following evidence controls are fixed:

| Missing or conflicting evidence | Forensic output |
| --- | --- |
| Original R source snapshot unavailable | `UNRESOLVED_NO_MATCH` |
| Only an obsolete source version remains | `UNRESOLVED_NO_MATCH` |
| Original nonce unavailable | `UNRESOLVED_NONCE` |
| Two candidate names have identical content | `UNRESOLVED_AMBIGUOUS` |

If a trusted source certificate or its underlying registered evidence is absent, the effect endpoint itself returns `UNRESOLVED`. **Candidate replay is not used as a substitute for live write authorization.** A matching candidate set offers conditional forensic information but does not certify source-access completeness.

## Run the experiment

Prerequisites are Linux, Docker, and access to the public container image and Python packages. The helper creates a temporary Python 3.12 environment with LangGraph 1.2.12, then executes the isolated processes in a disposable container.

```bash
bash experiments/trusted_custody/run.sh dev
bash experiments/trusted_custody/run.sh holdout
```

The generated artifacts are written to `_custody_runs/<partition>/`. They contain a read-only-auditable database, test oracle, random synthetic snapshots and a verification report. Never substitute real privileged material in this public test fixture.

Original completed Actions:

- [Development run 44464377771](https://github.com/risu-research/formal-exec-2609/actions/runs/44464377771)
- [Held-out run 44464512343](https://github.com/risu-research/formal-exec-2609/actions/runs/44464512343)
- [Pinned machine-readable evidence summary](../../results/trusted_custody_summary.json)

## Scope

This test uses a broker and worker with different real Linux identities, and a durable protected SQL effect path. It establishes a concrete reference-monitor implementation within the stated interface. It is **not** a proof of mediation across arbitrary network sockets, memory, operating-system administrators, existing unprotected caches, third-party vendors or compromised trusted code. The token is a bearer capability within this test, not a complete production identity system.

The 168 held-out executions reuse 14 designed fault types and six seeds. They do not represent independent deployed agents or legal matters, and they do not measure naturally occurring failure rates. The results isolate a feasible security improvement and a remaining evidence boundary. Wider deployment would require network egress restrictions, protected secrets outside the agent's process, policy-administration controls, and integration with the real external effect service.

The accepted manuscript remains unchanged. No GitHub release, Zenodo deposition or DOI has been created. Archival publication requires the author's explicit approval.
