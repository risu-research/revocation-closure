# Court-order coding audit

This dataset accompanies *After the Clawback: Revocation Closure in Agentic Legal Workflows*. Forty federal court-entered orders were selected for a clause-level study of information handling after privilege notices and related events.

## Files

- `orders.csv` lists 40 cases, their docket links, original strata and initial partitions.
- `codebook.csv` records the thirteen explicit-text coding categories and their thresholds.
- `frozen_520.csv` contains the original 40-by-13 binary labels.
- `source_clause_pins.csv` lists 47 indexed, source-linked positive clause notes available from the preliminary audit. They cover 27 orders.
- `reviewed_disagreements_77.csv` records 77 contested core-stratum cells with the original, second-pass and adjudicated values, plus source locations. Seventy-four adopted a changed value.
- `event_predicates_40.csv` keeps the later order-wide and event-triggered distinctions for all 40 orders, with their original public PDF links.

Run `python verify_public_coding.py` to check unique case and cell keys, original core-order frequencies, the core disagreement count, and the event-specific frequencies reported in the paper. All files use UTF-8 CSV.

## Interpretation

The initial 520 labels follow the original codebook. Later event questions distinguish whole-order treatment from actions triggered directly by a privilege claim. The reviewed disagreements cover a selected 77-cell core-stratum subset. The underlying historical search-query log was not preserved in full.

This release supports independent review of each published baseline cell and the event summary. A complete cell-by-cell reconstruction of the manuscript's 120 revised order-wide labels needs the full final adjudication table. The preliminary clause pins do not supply full-document negative checks for every zero.

Order PDFs remain at their linked public sources. The repository holds only our coding tables and short clause-location notes.

## Conditional order-wide reconciliation

The [120-cell adjudication ledger](adjudicated_changes_120.csv) and [complete conditional 520-cell table](conditional_520.csv) reconstruct the later order-wide labels from the original frozen matrix. [Methods and source-check flags](CONDITIONAL_CODING.md) distinguish that coding scope from the event-triggered predicates. Run `python verify_conditional_coding.py` in this directory to check all 120 changes and the 13-code totals.
