# Conditional court-order coding

The original coding table records 40 entered U.S. federal protective orders with 13 binary codes per order. The later order-wide review revised 120 of the 520 cells. Each revised cell is linked to its original value, a separately recorded second-pass decision, the final adjudicated value, a clause location, a short decision reason and the public order URL.

The original coding question and the later order-wide question cover different clause scopes. The conditional results therefore measure sensitivity to the coding definition. Event-triggered counts are recorded separately in `event_predicates_40.csv`.

## Data

- `frozen_520.csv` records the original 520 decisions.
- `adjudicated_changes_120.csv` records 120 individual changes with their source clauses, second-pass results and adjudication reasons.
- `conditional_520.csv` lists every original and conditional label, including 400 unchanged cells.
- `source_checks_pending.csv` identifies five targeted source checks whose original review records remain incomplete.
- `codebook.csv` defines the 13 coding categories.

## Reproduce

Run from this directory using Python 3.10 or later.

```bash
python verify_public_coding.py
python verify_conditional_coding.py
```

The verifier joins rows by order ID and code, checks all 120 adjudications against the frozen matrix, reconstructs the 520 final labels and recalculates the 13 category counts.

## Recorded outcomes

| Measure | Count |
| --- | ---: |
| Original positive labels | 262 |
| Conditional positive labels | 378 |
| Changed cells | 120 |
| Changes from 0 to 1 | 118 |
| Changes from 1 to 0 | 2 |
| Core 30 orders revised | 76 cells |
| Additional 10 orders revised | 44 cells |

The reviewed changes came from 74 adjudicated core disagreements, two further core omissions, 42 adjudicated supplementary disagreements and two further supplementary omissions.

The five pending checks concern precise PDF pages for paragraph 26 in the Daily News and Center for Investigative Reporting orders, and the full-order negative review for the named database code in Voltstar. The entered order text supports targeted clause readings. The full 520-label matrix has not received a new independent human recoding or an exhaustive negative-evidence audit. The 120 rows preserve the researcher's documented adjudications.
