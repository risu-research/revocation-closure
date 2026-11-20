# Court-order policy transfer test

This experiment tests a fixed lexical policy extractor on selected clauses from three court-entered protective orders. The source passages and author-coded reference duties are stored alongside the exact extractor used in the evaluation.

The first two orders contain 20 manually coded obligations. The extractor identified 13 actions and produced three complete seven-field obligations. The source-code-frozen evaluation on a third order identified zero of eight obligations. Both findings are retained in the recorded results.

A separate experiment replays 18 synthetic write requests against a local HTTP/SQLite recipient in two configurations. Cached authorization committed 11 prohibited effects. Current-policy checks reduced that count to two. Those two are the missing-notice scenarios and remain visible in the independent audit.

## Run

Python 3.10 or newer is sufficient. No additional Python packages are required.

```bash
python src/generic_policy_extractor.py --source sources/scoped_order_passages.json --out results/one_shot_policy_proposals.json
python src/score_frozen_holdout.py
python src/generic_policy_extractor.py --source confirmatory/new_order_passages.json --out confirmatory/one_shot_proposals.json
python confirmatory/score_code_frozen.py
python src/run_effect_study.py --output _runs/first
python src/independent_effect_auditor.py --folder _runs/first
python tests/check_public_reproduction.py
```

`tests/check_public_reproduction.py` also checks the source-code seal, archived scores, a fresh HTTP/SQLite run and a database-tampering control.

## Inputs

- [First two court excerpts](sources/scoped_order_passages.json) and [their coded obligations](gold/reference_duties.csv)
- [Fixed third-order excerpts](confirmatory/new_order_passages.json), [reference duties](confirmatory/new_gold.csv), and [source-code seal](confirmatory/SEAL_BEFORE_GENERATION.json)
- [Synthetic write matrix](gold/scenario_oracle.csv)

Each court excerpt includes its public filing URL and clause identifier. The reference obligations were coded by one researcher. The first two orders were read before the extractor was written. The third was selected after the extractor code was frozen. Results measure the selected clauses and fixed synthetic requests.

The write recipient uses newly generated disposable credentials and local loopback ports. The fresh audit reads persisted SQLite rows separately from the receiver. Run output stays in `_runs/`.

## Verify the files

```bash
sha256sum -c SHA256SUMS.txt
```
