# Verified trusted custody experiment

The public source for this module is in [experiments/trusted_custody](../experiments/trusted_custody). It is a prospective evaluation of a protected, process-separated source reader and guarded SQL effect service.

## Verified execution

| Split | Completed Actions | Artifact | Test conditions | Physically committed effects | SQL SHA-256 |
| --- | --- | --- | ---: | ---: | --- |
| Development | [44464377771](https://github.com/risu-research/formal-exec-2609/actions/runs/44464377771) | [14501865391](https://github.com/risu-research/formal-exec-2609/actions/runs/44464377771/artifacts/14501865391) | 56 | 20 | `3a4480abb0acf45917f8a5e4d9441a3745a584993d9898d5664c2df4acb3a1be` |
| Held-out | [44464512343](https://github.com/risu-research/formal-exec-2609/actions/runs/44464512343) | [14501497943](https://github.com/risu-research/formal-exec-2609/actions/runs/44464512343/artifacts/14501497943) | 168 | 60 | `7c27de50bd75ee392c1deba765808a6423e1d48bd3415b903a18cf0c7ccf302a` |

The original Actions archives were downloaded and extracted independently. The complete SQLite files passed `PRAGMA integrity_check`, and the standalone [independent_auditor.py](../experiments/trusted_custody/independent_auditor.py) reproduced the archived `audit.json` records exactly.

Auditor JSON SHA-256:
- Development `e8ed3ca857636e56f76506a0196565b5499455d5cb2340435f13d3529c04d138`
- Held-out `2406336bafa0c18fa3d3821f7c33e39079949ddb127e90bacb9e24269d721b18`

## Independent clean-room public reproduction

[Public-reproduction Actions run 44465097707](https://github.com/risu-research/formal-exec-2609/actions/runs/44465097707) cloned the public repository at commit `6766696e89c4a851228360022d3f38cfe11e2142`, verified all four code blob hashes and executed the documented `run.sh dev` from a fresh checkout. It reproduced the same 56-case decision and physical effect totals.

The job also made a disposable copy of the SQLite file and altered the source lineage of a committed effect. The independent SQL auditor failed with an assertion, as expected. It did not silently accept the modified record.

The public reproduction log is preserved in [Actions artifact 14500844983](https://github.com/risu-research/formal-exec-2609/actions/runs/44465097707/artifacts/14500844983).

## Source identity

- `trusted_broker.py`: Git blob `7c47d692e99d8d79c9557c8e2d11409b685a78a5`
- `agent_worker.py`: Git blob `95e0a3f45aee6b149f5bd79723f3a0c50a94fdf8`
- `integrated_driver.py`: Git blob `0291f3fc37c233af547668e424256a477ff7763c`
- `independent_auditor.py`: Git blob `2a33aa996bae26026216b184fb43278ea4a65883`

These source files were kept identical between the final development and held-out executions.

## Observed effect and evidence outcomes

The held-out matrix contains 14 designed scenarios in two policy fixtures repeated for six previously separated seeds. Each scenario has 12 executions.

Of the 168 held-out conditions, 156 resumed a historical pre-effect checkpoint. The other 12 attempted to read revoked R after notice and were blocked before a certificate or effect checkpoint was available. The 60 physically stored effects consist of 36 valid clean-source writes, 12 R-source writes before notice, and 12 writes after an explicit release. The 72 unresolved outcomes come from six evidence-fault scenarios, with 12 cases in each. The separate duplicate-control scenario contains 12 blocked second uses following the first permitted write.

- A revoked or mixed-source historical checkpoint produced no protected SQL effect after revocation.
- Source derivation from the revoked R file after the notice was denied.
- Valid, independently sourced K effects were preserved.
- Altered output, forged source labels, missing HMAC certificate, wrong flow and missing issue/read evidence each resulted in `UNRESOLVED`.
- A second use of a previously committed signed effect was blocked.
- The separate release fixture permitted the original R-derived effect after the policy state was explicitly restored.
- The untrusted UID 12002 was refused physical access to the source vault, HMAC key, administrator key and SQL ledger.
- Unauthenticated administrator operations and an uninstrumented source-read endpoint were unavailable to the worker.

The independent forensic checks also returned `UNRESOLVED_NO_MATCH` for a missing historical R snapshot and an obsolete R version, `UNRESOLVED_NONCE` for a missing nonce, and `UNRESOLVED_AMBIGUOUS` for multiple source identities with identical values. These forensic decisions do not themselves grant runtime authorization.

## Research interpretation

This is a **conditional effect-closure** result for a deliberately small trust boundary. The broker, not the ordinary agent, owns the protected bytes, provenance evidence and effect-writing channel. The experiment shows what becomes possible when those assumptions are enforced and verified on Linux.

It does not solve access through preexisting copied content, uncontrolled caches, third-party write APIs, compromised trusted software or arbitrary network egress. The threat model assumes the privileged orchestrator and broker are trusted. All source values are synthetic random bytes.

There is no newly published Zenodo release, DOI or tagged GitHub release for these results. The original accepted paper remains unchanged.
