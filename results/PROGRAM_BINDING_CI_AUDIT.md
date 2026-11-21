# Program-bound execution and approval-ablation reproduction

The public [program-binding experiment](../experiments/program_binding/README.md) now has a [GitHub Actions reproducer](../.github/workflows/verify-program-binding.yml). It starts two fresh test runs in a disposable Linux environment, with separate runner, broker and recipient user identities. One run uses the existing program approval list. The other admits only one additional program hash, that of `literal_launder.py`. Both runs execute the independent signed-record and SQL audit.

## Verified fresh run

- [Successful Actions run 44845496015](https://github.com/risu-research/revocation-closure/actions/runs/44845496015), source commit `ddbc40e114ccbd0c9990c60a2ea4aa2d25c5eb5f`.
- [Artifact 14682188722](https://github.com/risu-research/revocation-closure/actions/runs/44845496015/artifacts/14682188722) retains two SQLite recipient snapshots, 24 signed output bundles, separate public trust keys, decision lists, and both independent audit reports.
- Fresh cryptographic keys were generated for each mode. The source programs and source pins remained the same. Signatures and database-file hashes therefore differ across fresh runs.

| Measure | Original approval set | Literal program also approved |
| --- | ---: | ---: |
| Python execution attempts | 17 | 17 |
| Signed program completions | 12 | 12 |
| Executions ending without a seal | 5 | 5 |
| Recipient submissions | 17 | 17 |
| Allowed | 4 | 5 |
| Blocked | 6 | 6 |
| Held | 7 | 6 |
| Durable SQL effect rows | 4 | 5 |
| SQL attempts rows | 12 | 13 |
| Pre-admission rejection rows | 5 | 4 |
| Signed broker bundles independently verified | 12 | 12 |

The 17 recipient submissions consist of 12 signed program results, four altered-proof submissions and one additional reuse submission. The 17 execution attempts are a separate count. The source code ran successfully for `literal_launder.py` in both modes. Only recipient admission changed.

## What the approved literal test records

The literal program contains the synthetic bytes of the revoked `iottie_PRIV` source. Its only broker-observed read is `iottie_CLEAN`. Both broker signatures correctly bind the observed read, program hash and returned output bytes. The original recipient held the effect because the program hash was not approved. Adding this hash to the approval list made one additional write eligible at the recipient, with the same source fixtures, program code, and policy rules.

The fifth SQL effect references an `output_sha256` matching the signed literal-bearing output. The SQL `synthetic_payload` column contains the fixed value `SYNTHETIC_EFFECT`; the protected literal's raw bytes are retained in the signed output bundle rather than that column. This distinction is visible in the archived SQLite tables.

The original verifier and an independently authored offline checker both confirmed all 24 Ed25519 broker-signed bundles, six source pins per mode, the signed owner notices, recipient decisions, and physically stored SQL rows. A disposable copy with the literal effect's output hash altered failed the independent record check.

## Recheck the archived record

Download and extract the Actions artifact. From the archive root, check the six retained file hashes:

```bash
sha256sum -c reproduce-sha256.txt
```

With the public repository and Python `cryptography==46.0.4` installed, copy the two extracted result directories to `experiments/program_binding/ci_evidence/` and run the independent original auditor against each:

```bash
cd experiments/program_binding
python tests/independent_stage_q_audit.py . ci_evidence/fresh_baseline
python tests/independent_stage_q_audit.py . ci_evidence/fresh_ablation
```

The fresh reproduction tests the supplied source code, named system-call controls, signature verification, program admission and recipient-owned SQL effect path. The signatures identify delivered code bytes and broker-observed API use. The literal control identifies code-embedded data as a further input to review during program approval.
