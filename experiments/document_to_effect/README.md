# Document-to-effect replay

A deterministic agent reads a public court-order summary and synthetic discovery records through a local HTTP source service. The agent prepares a short work note, receives a signed write permit and submits the note to a separate HTTP/SQLite recipient.

The evaluation tests permits issued before a producer notice, current-policy checks at the recipient, owner credentials, incomplete read evidence and recipient restarts. A read-only auditor checks signed messages, recorded source reads, actual SQLite rows and a separate synthetic-source oracle.

## Run the experiment

Tested with Python 3.13.5 and cryptography 46.0.4. From this directory, run:

```bash
python -m pip install -r requirements.txt
python tests/reproduce.py
```

The test starts its own local services, runs all 46 write attempts and compares the output with `recorded/expected.json`. It also runs the independent SQL auditor. Temporary output is cleaned up after the test.

To inspect the evidence from one run:

```bash
python code/run.py --out results/local_run
python code/independent_audit.py results/local_run
```

The output includes read receipts, signed actor events, permits, requests, recipient responses and SQLite databases. Signing keys are generated for each run. The runner deletes the temporary source-signing key when it finishes.

## Recorded results

| Outcome | Count |
| --- | ---: |
| Write attempts | 46 |
| Persisted writes | 17 |
| Writes blocked after revocation | 13 |
| Requests held for invalid evidence | 14 |
| Duplicate writes blocked | 2 |
| Unsafe writes in the control conditions | 9 |

The 46 attempts cover two manually selected court-policy fixtures. The researcher-defined cases include a stale signed permit, an unacknowledged notice, an untracked content dependency and receiver self-discovery. The independent auditor reconstructs decisions using signed requests and physical storage records.

## Source material

The input combines short excerpts from [Camm v. Reach Financial, Dkt. 38, §20](inputs/COURT_SOURCES.md) and [Napoli v. Meta Platforms, Dkt. 37, §13](inputs/COURT_SOURCES.md) with invented discovery text. The court passages are linked to the public source documents. The remaining records, deadlines in the test harness and policy events are constructed test inputs.
