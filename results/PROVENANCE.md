# Verified court-policy experiment

The public repository stores a byte-exact copy of the JSON generated in the independent computation repository.

- Source commit: [158a1d455134b82758bd3bb1d0311b2ecf2a6512](https://github.com/risu-research/formal-exec-2609/commit/158a1d455134b82758bd3bb1d0311b2ecf2a6512)
- Executed source branch: `exec/j-l62a9b`
- GitHub Actions run: [44453790030](https://github.com/risu-research/formal-exec-2609/actions/runs/44453790030)
- Original Actions artifact ID: `14497271280`, archive `j-l62a9b-court-policy`
- Original source SHA-256: `e116d0aba2ead280ee783945d0200ed33203f55ad035bb51febdae089db6591d`
- Original result SHA-256: `02a53546dc4dcf3b5e5ecf7ce59ace8d66e3d125294cd55a867a0044824c587b`
- Public result blob SHA-1: `a144354a09aab3b5d63dbaa847d4605460226d25` (matches the blob hash of the original unmodified JSON)
- Execution package: Python 3.12, `langgraph==1.2.12`; local SQLite effects. The action ran on Ubuntu and was successful.

Results: 25 manually mapped, predeclared policy fixtures pass, two additional deadline wording assertions pass, and eight actual historical checkpoint replays produce the expected precommitted outcomes.

The eight replays are synthetic fault-injection scenarios, not eight real-case tests. Acosta covers no guard, cached approval, current approval, and clean content. NECEC covers current approval, unknown provenance, falsely complete provenance, and a separately verified withdrawal phase.

These tests do not prove the correctness of the manual clause-to-policy mapping in all legal contexts. They also do not perform actual provider deletion, timestamp-based court deadline calculations, or fully automated legal interpretation. The external docket PDFs remain authoritative for their respective legal obligations.

## Re-run

From repository root:

```bash
python -m pip install 'langgraph==1.2.12'
python experiments/court_policy/legal_order_probe.py
python tests/verify_recorded_results.py
```

The first command creates `legal_order_result.json` in the working directory. The second checks both the archived result and the rerun when present. The frozen execution source, original artifact and this published JSON are connected through their SHA-256 and Git blob hashes.

Earlier independent stack probes remain documented separately:

- [In-memory checkpoint effect replay](https://github.com/risu-research/formal-exec-2609/actions/runs/44450492824)
- [PostgreSQL 16 checkpoint effect replay](https://github.com/risu-research/formal-exec-2609/actions/runs/44450716347)

They support a different experimental layer and are not counted in this experiment's 33 assertions.
