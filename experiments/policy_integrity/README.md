# Policy integrity at the recipient

This experiment checks a manually reviewed legal-policy representation before a recipient writes a new document. It follows a deterministic document worker through actual HTTP source reads, signed write permits and a separate SQLite recipient.

The policy input contains 18 selected rules and eight actor-and-deadline records from iOttie, Camm, Napoli and Rule 26. Each rule carries a court-source location. The structural checker compares that representation with pinned source records and rejects changes to selected actors, clocks, source links, rules and exceptions.

## Run

Use Python 3.11 or later. The test starts HTTP services on available localhost ports and generates new signing keys for each run.

```bash
python -m pip install -r requirements.txt
python reproduce.py
```

The runner builds the policy representation from the fixed inputs, checks its hash, runs both recipients against the same 46 synthetic scenarios, independently audits their stored SQL effects, tests 13 policy mutations and checks whether the auditor rejects an altered stored document.

## Recorded results

| Measure | Baseline recipient | Checked recipient |
| --- | ---: | ---: |
| HTTP write attempts | 46 | 46 |
| Stored SQL effects | 17 | 12 |
| Unsafe control effects | 9 | 4 |
| Clean effects preserved | 8 | 8 |

The checker detected all 13 injected policy mutations. Twelve of them were also tested through the HTTP recipient. Each protected write was held, and the corresponding clean write was retained.

The four remaining unsafe control effects arise outside the structural check's authority. Source coverage and notice delivery are evaluated separately. The policy mapping is based on selected clauses reviewed by the researcher, and the test applies fixed synthetic records. Its results concern the specified policy representation and recipient behavior.

## Files

- `inputs/` contains the selected rule and deadline records, the typed policy and synthetic documents.
- `src/build_a0_ir.py` builds the typed policy from the fixed inputs.
- `src/a0_assurance.py` checks policy structure and supplies the receiver gate.
- `stage_s_original/code/` runs the original HTTP recipient and document worker.
- `stage_s_hardened/code/` runs the recipient with the policy check.
- `tests/` compares stored effects, exercises 13 policy mutations and tests independent SQL tamper detection.
- `expected_results.json` records the audited counts.

Generated keys, request logs and SQLite databases stay under `results/`, which Git ignores. Each run uses fresh synthetic credentials.
