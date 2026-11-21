# Program-bound execution at a revocation-aware recipient

This experiment runs small Python transformations with protected synthetic sources. A separate broker controls source reads and signs their observed dependencies, output bytes, and program digest. A recipient verifies that evidence and its locally acknowledged revocation policy before writing to SQLite.

## Reproduce

Use a disposable Linux container or VM with Python 3.12+, `libseccomp.so.2`, and root access inside that disposable environment. The scripts create temporary unprivileged identities and remove their private keys after each run.

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python -m experiments.trusted_transform.run_stage_q --out fresh_baseline
PYTHONPATH=. python tests/independent_stage_q_audit.py . fresh_baseline
PYTHONPATH=. python -m experiments.trusted_transform.run_stage_q --approve-literal --out fresh_ablation
PYTHONPATH=. python tests/independent_stage_q_audit.py . fresh_ablation
python tests/check_expected_metrics.py
```

## Results

| Condition | Signed program completions | Rejected executions | Recipient allows | Recipient blocks | Recipient holds | SQL effects |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Approved programs only | 12 | 5 | 4 | 6 | 7 | 4 |
| Literal program also approved | 12 | 5 | 5 | 6 | 6 | 5 |

The second run adds the digest of `programs/literal_launder.py` to the recipient's trusted program list. The program reads only `iottie_CLEAN` from the broker, but its code contains bytes identical to the revoked synthetic source. Once admitted, the recipient commits that output. The independent audit verifies the literal's bytes, its clean read record, the approval list and the stored SQL effect.

The runner measures delivered program bytes and recorded output. The approved-program registry controls which signed outputs the recipient will store. It does not prevent an unapproved script from executing in the test runner. Source-origin review must include program literals and other inputs already present before the broker's reads. The [fresh Actions reproduction and SQL audit](../../results/PROGRAM_BINDING_CI_AUDIT.md) records both approval conditions and retains the signed evidence.

The [test matrix](STAGE_Q_TEST_MATRIX.csv) lists the original cases. The [expected counts](recorded_outcomes.json) separate the original run from the admission ablation. The auditor checks source pins, signatures, code/launcher digests, recorded notice epochs, output hashes, and physical SQLite effects. Its four proof-mutation controls must all fail verification.

Source material and court-policy states are synthetic test fixtures. The authorization boundary is the locally controlled recipient and the configured Linux process identities.
