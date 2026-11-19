# Recipient-owned current authorization

## Purpose

An earlier module in this repository [enforces source custody with a trusted broker](../trusted_custody/PROTOCOL.md). It prevents untrusted agents from directly reading its source vault and checks the broker's own SQLite effect endpoint. That does **not** establish that an independent downstream recipient will reject a stale permission or an unmediated write.

This experiment puts the effect ledger and current revocation policy **inside a separate recipient service**. A historical LangGraph checkpoint contains a write capability valid before a legal-policy change. The experiment resumes that checkpoint after the change and observes whether the recipient physically persists a new write.

The experimental design compares four recipient security boundaries, not four novel algorithms.

| Mode | Recipient checks | Insecure condition being isolated |
| --- | --- | --- |
| `open` | No write authorization | Public target can be written directly |
| `static` | HMAC-signed, one-use, audience-bound old capability | Valid old permission survives source revocation |
| `live` | Same permit plus currently acknowledged recipient revocation, in one SQLite transaction | Target can block old rights after it receives notice |
| `owner_live` | `live` plus owner credential stored outside the agent process | Untrusted worker cannot write directly using a copied permit |

The source permission is signed **before** revocation. The recipient owns the HMAC signing secret, policy database and physical effect ledger. The issuer's originally asserted source list and the experiment's separately withheld oracle truth are distinct. The untrusted worker can hold and alter the signed token, but cannot forge the signature.

A separate **owner relay** owns the additional recipient write credential. It does not control the recipient's revocation ledger. The recipient checks token, owner credential and current policy at the actual write transaction. The test deliberately allows the worker to call the relay with a valid token. This tests recipient-side checks, not a comprehensive user-identity or approval system.

## Process and state separation

On the GitHub Actions Linux container:

- Recipient process: UID 12003, with private signer/admin secrets and SQLite effect database.
- Owner relay: UID 12001, with a separate write credential.
- Untrusted LangGraph agent: UID 12002, without access to the relay's owner credential.
- Test orchestrator: trusted root solely for creation, simulated notice delivery and independent final evidence collection.

The worker's direct key-read attempt must receive `ACCESS_DENIED`. It tries a direct HTTP write for every `owner_live` case, and the target must deny that direct call before the legitimate mediated attempt. The receiver remains independently controlled and checks both attempts.

Each workflow creates a real LangGraph historical checkpoint before the effect, repairs the latest thread state, then replays the historical checkpoint. It invokes a real LangChain `@tool` wrapper that sends HTTP requests to the independent recipient or owner relay. The recipient's actual SQL rows, not the workflow return message, determine effect success.

## Frozen experimental protocol

- Two manually specified legal-policy contexts: Acosta producer notice and NECEC pending claim.
- Twelve fault and control cases.
- Four recipient modes.
- Development seeds 211 and 212.
- Held-out evaluation seeds 8211 through 8216.

That yields 192 development and **576 held-out synthetic checkpoint replays**. The fixed scenarios include R-derived and mixed-source permission reuse, independently clean work, pre-notice permitted writes, a later explicit policy release, a forged source label, altered body, wrong audience, missing credential, duplicate use, falsely clean **original issuance**, and **notice never delivered** to the recipient.

The same five code files were frozen before the held-out run. Scenario seeds vary opaque identifiers and synthetic output content, not real-world legal facts.

## Held-out results

Each mode sees 144 repeated synthetic conditions.

| Recipient mode | New writes based on revoked R after owner notice | Physical SQL effects | Clean valid control writes |
| --- | ---: | ---: | ---: |
| Open endpoint | 60 | 156 | 36 |
| Pre-notice signed permit only | 48 | 96 | 24 |
| Recipient current-policy check | 24 | 72 | 24 |
| Recipient current-policy + owner credential | 24 | 72 | 24 |

The 24 unsafe writes in **each** current-policy mode consist of two specifically retained counterexamples:

- 12 cases where the recipient did **not receive** the owner's revocation update. Its local state remained permissive.
- 12 cases where the authorized issuer signed a **false-clean source claim**. A signature does not certify a mistaken issuer's semantic correctness.

Accordingly, among revoked-source scenarios with **correct issuer provenance and an acknowledged recipient update**, the last two modes physically persisted **zero** unauthorized writes. The recipient's independent SQL transaction serializes its update and effect, eliminating the tested check/write gap relative to an acknowledged update.

The `owner_live` recipient rejected **144/144 direct agent attempts**. Legitimate clean-source work still completed through the owner relay, and a one-use token could not be used twice. The owner credential only closes the direct write path to this protected recipient. It does not stop an agent from contacting a completely separate public webhook.

These are fixture-conditioned results. Repeated seeds do not create independently sampled legal cases or actual frequency estimates. The explicit failure controls belong in any scientific summary.

## Independent verification

The recipient process stops before its database is copied. The recorded SQLite WAL is checkpointed into the standalone DB file, journal mode switches to DELETE and `PRAGMA integrity_check` must return `ok`. A separate read-only offline auditor reconstructs all recipient policy epochs, verifies signed issuance claims against the issuer records, checks actual SQL effects, compares source truth from a separate pre-created oracle manifest and recomputes both safety and clean-preservation metrics.

The original Actions archives were independently downloaded and opened in a separate local environment. Their full SQL effects and audit results matched. A disposable copy with one modified physical effect row was rejected by the independent auditor.

- [Development run](https://github.com/risu-research/formal-exec-2609/actions/runs/44467270022) and archive `14502592760`
- [Held-out run](https://github.com/risu-research/formal-exec-2609/actions/runs/44467406356) and archive `14503131178`
- [Frozen outcome metrics and file hashes](../../results/recipient_authority_summary.json)

## Public reproduction

Requires Linux and Docker, and network access to fetch the published Python package/runtime image. From the public repository root:

```bash
bash experiments/independent_recipient/run.sh dev
bash experiments/independent_recipient/run.sh holdout
```

The process creates fresh test-only secrets for each run and deletes its private temporary key directories. Generated evidence is stored under `_recipient_runs/<partition>`. Never use genuine legal work-product or live API credentials in the synthetic test harness.

## Relation to earlier work and claim limits

This design applies longstanding least-privilege, reference-monitor and recipient-side policy evaluation ideas. The [Macaroons paper](https://research.google/pubs/macaroons-cookies-with-contextual-caveats-for-decentralized-authorization-in-the-cloud/) motivates confined/delegated capabilities. [AWS IAM documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html) similarly describes recipient-side allow/deny evaluation. These are prior designs, not ideas claimed as new here.

The contribution of this test is the **legal revocation timing and downstream-effect boundary** under real checkpoint replay, with independent physically recorded writes, preservation controls and explicit failure counterexamples.

A compliant result for one protected recipient does **not** prove control of arbitrary external destinations, user-controlled caches, preexisting disclosures, compromised privileged code or recipients that cannot acknowledge new revocation. A protected service with a stale policy may permit old rights, as our counterexample directly demonstrates. The test is a constructed independent HTTP/SQLite recipient, not an actual legal platform or cloud IAM deployment.

The previously submitted paper remains unchanged. No GitHub release, Zenodo deposit or DOI has been made. Such release requires explicit author approval.
