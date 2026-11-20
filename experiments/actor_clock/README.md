# Actor, deadline and recipient replay

This experiment replays signed synthetic source-output evidence through an independent recipient. The recipient checks actor roles, dated court events, deadline triggers, source dependencies and the policy that applies when it commits each write.

Six recipient instances process 17 external-effect requests. Five requests create SQL rows, including one deliberately unsafe missed-notice control. The study also records three restricted counsel archives and one challenge-copy event. Eight duty templates and 12 date unit tests cover deadline calculation and actor-specific completion.

## Reproduce

The audit and unit tests run with Python 3.11 or later and `cryptography` (Ed25519 support). A fresh run needs a disposable Linux environment with root privileges to create separate unprivileged recipient and worker identities. Use an isolated container or VM.

```bash
python -m pip install 'cryptography>=42,<48'
python -m unittest discover -s tests -p 'test_*.py' -v
python -m stage_r.run_study --out /tmp/actor_clock_fresh
python tests/independent_audit.py /tmp/actor_clock_fresh
python tests/check_public_reproduction.py /tmp/actor_clock_fresh
```

The runner creates new synthetic signing keys for each run, starts isolated Unix-socket recipients, submits signed source bundles and stops each recipient before copying its database. The auditor reads physical SQLite rows and independently checks the signed requests, event records and deadlines. A new run produces the same counts with different signatures and database hashes.

## Source records

- [Eight source-linked duty fixtures](source_stage_n/R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER.csv)
- [Signed synthetic read and output bundles](source_stage_q/)
- [Recipient implementation](stage_r/recipient.py) and [independent auditor](tests/independent_audit.py)
- [Recorded expected counts](recorded_outcomes.json)

The duty entries were selected and coded from public orders. The experiment uses a deliberately specified test calendar. Previously generated synthetic transform attestations remain fixed; the recipient, clock events, actor signatures and effect commits are generated anew. A recipient with no delivered revocation notice remains permissive in the missed-notice control.

## Verify the files

```bash
sha256sum -c SHA256SUMS.txt
```
