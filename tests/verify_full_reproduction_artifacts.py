#!/usr/bin/env python3
"""Verify every archived group produced by the full public Actions workflow."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

GROUPS = {
    "public-artifact-static-audit",
    "actor-clock-full-evidence",
    "program-binding-reproduction",
    "document-to-effect-two-full-runs",
    "policy-integrity-two-runs",
    "full-checkpoint-provenance",
    "full-external-effects",
    "full-observed-tool-reads",
    "full-trusted-source-custody",
    "full-independent-recipient",
}
SAFE_TEXT_PATTERNS = {
    "key-material": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "access-token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9_]{28,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "personal-email": re.compile(rb"\b[A-Za-z0-9._%+-]+@(?:gmail|hotmail|outlook|yahoo|protonmail|web)\.[A-Za-z]{2,}\b", re.I),
    "personal-path": re.compile(rb"[A-Za-z]:\\Users\\[^\\\s]+\\|/home/oai/|/mnt/data/"),
}

def sql_count(path, table):
    assert path.is_file(), path
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok", path
        return connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        connection.close()

def collect(root):
    assert root.is_dir(), root
    existing = {p.name for p in root.iterdir() if p.is_dir()}
    assert GROUPS <= existing, {"missing": sorted(GROUPS - existing)}
    manifest = []
    for group in sorted(GROUPS):
        for path in sorted((root / group).rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()
            name = path.relative_to(root).as_posix()
            for rule, pattern in SAFE_TEXT_PATTERNS.items():
                assert not pattern.search(data), {"security_rule": rule, "file": name}
            assert path.suffix.lower() not in {".key", ".pem", ".p12", ".pfx"}, name
            manifest.append({
                "path": name, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest()
            })
    fixture = root / "full-checkpoint-provenance"
    court = json.loads((fixture / "legal_order_result.json").read_text())
    provenance = json.loads((fixture / "provenance_holdout_result.json").read_text())
    assert (court["status"], court["fixture_passed"], court["replay_passed"]) == ("PASS", 25, 8)
    assert provenance["asserted_expected_outcomes"] == 2160 and provenance["passed"]
    static = json.loads(
        (root / "public-artifact-static-audit" / "public-artifact-audit.json").read_text()
    )
    assert static["status"] == "PASS" and not static["errors"]
    results = {
        "court_fixtures": 25,
        "court_checkpoint_replays": 8,
        "provenance_executions": 2160,
        "external_sql_writes": sql_count(
            root / "full-external-effects" / "effects.sqlite", "writes"),
        "observed_read_sql_effects": sql_count(
            root / "full-observed-tool-reads" / "evidence.sqlite", "effects"),
        "trusted_custody_sql_effects": sql_count(
            root / "full-trusted-source-custody" / "ledger.sqlite", "effects"),
        "independent_recipient_sql_effects": sql_count(
            root / "full-independent-recipient" / "recipient.sqlite", "effects"),
        "program_baseline_effects": sql_count(
            root / "program-binding-reproduction" / "fresh_baseline" /
            "recipient_snapshot.sqlite", "effects"),
        "program_approved_literal_effects": sql_count(
            root / "program-binding-reproduction" / "fresh_ablation" /
            "recipient_snapshot.sqlite", "effects"),
    }
    actor = root / "actor-clock-full-evidence"
    actor_dbs = sorted(actor.glob("*_effects.sqlite"))
    assert len(actor_dbs) == 6, len(actor_dbs)
    results["actor_clock_sql_effects"] = sum(sql_count(p, "legal_effects") for p in actor_dbs)
    results["actor_clock_write_attempts"] = sum(
        sql_count(p, "legal_effect_attempts") for p in actor_dbs
    )
    doc = root / "document-to-effect-two-full-runs"
    for n in (1, 2):
        folder = doc / f"ci_trial_{n}"
        dbs = [p for p in folder.glob("*.sqlite") if p.name != "source_reads.sqlite"]
        assert len(dbs) == 5, (n, len(dbs))
        results[f"document_trial_{n}_effects"] = sum(sql_count(p, "effects") for p in dbs)
        results[f"document_trial_{n}_attempts"] = sum(sql_count(p, "attempts") for p in dbs)
        summary = json.loads((folder / "summary.json").read_text())
        assert (
            summary["attempts"], summary["persisted"],
            summary["oracle_unsafe_persisted"]
        ) == (46, 17, 9)
    policy = root / "policy-integrity-two-runs"
    for n in (1, 2):
        folder = policy / f"policy-integrity-{n}" / "results"
        for study in ("stage_s_baseline_rerun", "a0_enforced_primary"):
            dbs = [
                p for p in (folder / study).glob("*.sqlite")
                if p.name != "source_reads.sqlite"
            ]
            assert len(dbs) == 5, (study, len(dbs))
            results[f"policy_trial_{n}_{study}_effects"] = sum(
                sql_count(p, "effects") for p in dbs
            )
            results[f"policy_trial_{n}_{study}_attempts"] = sum(
                sql_count(p, "attempts") for p in dbs
            )
        m = json.loads((folder / "a0_mutation_results.json").read_text())["totals"]
        assert (
            m["injected_mutations"], m["detected_by_compiler"],
            m["mutations_tested_against_recipient"],
            m["mutated_protected_source_writes_persisted"],
            m["mutated_clean_source_writes_preserved"]
        ) == (13, 13, 12, 0, 12)
    expected = {
        "external_sql_writes": 720,
        "observed_read_sql_effects": 360,
        "trusted_custody_sql_effects": 60,
        "independent_recipient_sql_effects": 396,
        "program_baseline_effects": 4,
        "program_approved_literal_effects": 5,
        "actor_clock_sql_effects": 5,
        "actor_clock_write_attempts": 17,
        "document_trial_1_effects": 17,
        "document_trial_2_effects": 17,
        "document_trial_1_attempts": 46,
        "document_trial_2_attempts": 46,
        "policy_trial_1_stage_s_baseline_rerun_effects": 17,
        "policy_trial_2_stage_s_baseline_rerun_effects": 17,
        "policy_trial_1_a0_enforced_primary_effects": 12,
        "policy_trial_2_a0_enforced_primary_effects": 12,
        "policy_trial_1_stage_s_baseline_rerun_attempts": 46,
        "policy_trial_2_stage_s_baseline_rerun_attempts": 46,
        "policy_trial_1_a0_enforced_primary_attempts": 46,
        "policy_trial_2_a0_enforced_primary_attempts": 46,
    }
    for name, wanted in expected.items():
        assert results[name] == wanted, {
            "measure": name, "wanted": wanted, "observed": results[name]
        }
    return {
        "schema": "full-public-reproduction-artifact-audit-v1",
        "status": "PASS", "source_commit": os.getenv("GITHUB_SHA"),
        "artifact_groups": len(GROUPS), "files_hashed": len(manifest),
        "results": results, "files": manifest
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = collect(args.directory)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    print(json.dumps(
        {k: v for k, v in report.items() if k != "files"}, indent=2
    ))

if __name__ == "__main__":
    main()
