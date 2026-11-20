#!/usr/bin/env python3
"""Check numerical consistency across the six archived evaluation summaries."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / "results" / name).read_text())


court = read("court_policy_result.json")
assert court["fixture_count"] == court["fixture_passed"] == 25
assert court["replay_count"] == court["replay_passed"] == 8

provenance = read("provenance_stress_summary.json")["evaluation"]
assert provenance["checks"] == 2160
for mode, unsafe, clean in (
    ("cached", 400, 320),
    ("embedded", 160, 240),
    ("receipt", 80, 160),
):
    case = provenance["by_guard"][mode]
    assert case["total"] == 720
    assert (case["affected"], case["clean"]) == (400, 320)
    assert (case["unauthorized_effects"], case["clean_effects_preserved"]) == (
        unsafe, clean
    )

external = read("external_effects_summary.json")["splits"]["holdout"]
assert external["cases"] == 1152
for mode, unsafe, clean, races in (
    ("cached", 216, 120, 48),
    ("client_precheck", 96, 48, 48),
    ("sink_atomic", 48, 48, 0),
):
    case = external["by_guard"][mode]
    assert (case["cases"], case["revoked_at_commit"], case["clean_cases"]) == (
        384, 216, 120
    )
    assert (
        case["unsafe_writes"],
        case["clean_writes_preserved"],
        case["race_unsafe"],
    ) == (unsafe, clean, races)

reads = read("tool_read_nondeterminism_summary.json")["splits"]["heldout"]
assert reads["cases"] == 540
for mode, unsafe, clean in (
    ("cached", 84, 72),
    ("declared", 36, 48),
    ("tool_trace", 12, 48),
):
    case = reads["guards"][mode]
    assert (case["cases"], case["affected"], case["clean"]) == (180, 84, 84)
    assert (case["revocation_violation"], case["clean_work_preserved"]) == (
        unsafe, clean
    )

custody = read("trusted_custody_summary.json")["heldout"]
assert (
    custody["cases"],
    custody["revoked_derived_effects_committed_during_revocation"],
) == (168, 0)
assert (
    custody["clean_scenarios_committed"],
    custody["missing_or_modified_evidence_cases_abstained"],
) == (36, 72)

recipient = read("recipient_authority_summary.json")["evaluation"]
assert recipient["cases"] == 576
for mode, unsafe in (
    ("open", 60),
    ("static", 48),
    ("live", 24),
    ("owner_live", 24),
):
    case = recipient["by_mode"][mode]
    assert (case["cases"], case["unsafe_after_owner_notice"]) == (144, unsafe)
assert (
    recipient["correctly_declared_with_acknowledged_revocation_unsafe_per_live_mode"]
    == 0
)

print("PASS: six recorded evaluation summaries match the reported totals")
