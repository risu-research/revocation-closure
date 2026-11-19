# Independently verified downstream effects

## Experimental source and reference runs

Public research artifact: [risu-research/revocation-closure](https://github.com/risu-research/revocation-closure)

Compute repository: [risu-research/formal-exec-2609](https://github.com/risu-research/formal-exec-2609), branch exec/j-sink731.

The source of all three experimental Python modules was identical in the final development and held-out runs.

| Source module | SHA-256 | Git blob SHA-1 |
| --- | --- | --- |
| external_effect_sink.py | 3363da6f914fce33662c5b7349ddc05f316427b99235f9a4a2e35cc720840111 | 30f4d17d19550e8549cb974055279a0972341510 |
| external_effect_runner.py | ca4b44189ab50f21f68c467f15ea8b942feb570f4b8dbae177c83e4d82d9ab8b | c41adef808930ceccfbc00efcd1b5bc71446a255 |
| external_effect_auditor.py | 023c78bb9f808692afe97b9f3f8e938318cee347c91da1fbb4f1962433a6ff92 | 7b4f75a4ad91bb74e47c294d02839b089f90e8b9 |

- [Final development run 44457578111](https://github.com/risu-research/formal-exec-2609/actions/runs/44457578111). Artifact ID 14498955334. 384 historical checkpoint replays. The physically archived SQL database contains 240 writes.
- [Final held-out run 44457583262](https://github.com/risu-research/formal-exec-2609/actions/runs/44457583262). Artifact ID 14498647239. 1,152 historical checkpoint replays. The physically archived SQL database contains 720 writes.
- [Public code checkout, replay and malicious-storage-mutation negative-control run 44458667884](https://github.com/risu-research/formal-exec-2609/actions/runs/44458667884). Its code and rerun instructions were taken from public repository commit a011a8b0c1de0ffa86d6d0601a99ac6d392a9fe9. The independent auditor rejected a deliberately altered stored payload.
- [Full evaluation summary](external_effects_summary.json), including fixed seeds, observed guard metrics and complete evidence links.

## Measured physical outcome

The final held-out split evaluates 384 fixed scenario/seed/order combinations per guard.

| Guard | Unauthorized stored writes | Clean-source writes preserved | Unsafe race writes |
| --- | ---: | ---: | ---: |
| Cached approval | 216 of 216 affected | 120 of 120 | 48 of 48 |
| Client precheck | 96 of 216 affected | 48 of 120 | 48 of 48 |
| Sink-transaction check | 48 of 216 affected | 48 of 120 | 0 of 48 |

The remaining 48 unauthorized writes under the sink-transaction check arise from falsely complete source receipts. The observer detects the resulting persisted effects; the module has no external rollback capability.

The full database and oracle manifest are retained in each run's Actions artifact. The downloadable recovery handoff package also carries those original archives. All run and evidence hashes match the public source summary.

## Integrity finding and correction

In an earlier superseded development archive, SQLite WAL records had not been merged into the single SQL database file before artifact upload. The live observer had read the full state, but the copied database omitted some persisted writes. Both final runs now checkpoint the WAL, switch to DELETE journal mode, and require SQLite integrity_check=ok before the read-only audit and upload.

The final downloaded ZIPs were independently opened again in a separate Python environment. Their DB row counts, physical integrity checks, and stored report digests matched the original Actions audits.

The raw Actions artifacts and all related code remain reproducible. Superseded runs and incomplete database archives are excluded from the reported results.

## Scope and limits

The setup is synthetic and runs a separate localhost HTTP service and persisted SQLite store. It demonstrates an actionable authorization race and a residual incomplete-lineage boundary in the constructed test harness. It does not validate real cloud APIs, independent vendor provenance claims, legal compliance, or deployed fault prevalence. The test fixture uses LangGraph InMemorySaver. A separate earlier study exercised PostgresSaver for a simpler state replay.

The newly added module does not change the submitted paper's original experiments. No GitHub release, Zenodo artifact publication or DOI has been created. Publication requires explicit author approval.
