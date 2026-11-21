#!/usr/bin/env python3
"""Run an unchanged historical seven-case script and retain its actual SQLite files."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sqlite3
import sys
import tempfile

ORIGINAL_TEMP_DIRECTORY = tempfile.TemporaryDirectory

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    original = args.source.resolve()
    assert original.is_file(), original
    out = Path.cwd()
    preserved = out / "sql-effects"
    preserved.mkdir(exist_ok=True)
    captured = []

    class RetainedDirectory(ORIGINAL_TEMP_DIRECTORY):
        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                dbs = sorted(Path(self.name).glob("*.sqlite"))
                if dbs:
                    assert not captured, "More than one SQL-effect directory"
                    assert len(dbs) == 7, ("Expected seven original cases", len(dbs))
                    for db in dbs:
                        destination = preserved / db.name
                        assert not destination.exists(), destination
                        shutil.copyfile(db, destination)
                    captured.extend(d.name for d in dbs)
            return super().__exit__(exc_type, exc, tb)

    tempfile.TemporaryDirectory = RetainedDirectory
    try:
        runpy.run_path(str(original), run_name="__main__")
    finally:
        tempfile.TemporaryDirectory = ORIGINAL_TEMP_DIRECTORY

    assert len(captured) == 7, ("Missing captured SQLite databases", captured)
    record = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert record["all_assertions_passed"] and record["case_count"] == 7
    verified = []
    for case in record["cases"]:
        db = preserved / (case["name"] + ".sqlite")
        assert db.exists(), db
        conn = sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True)
        try:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", db
            raw = conn.execute(
                "SELECT seq,payload,policy_version FROM effects ORDER BY seq"
            ).fetchall()
        finally:
            conn.close()
        assert [list(row) for row in raw] == case["rows"], case["name"]
        verified.append({
            "case": case["name"],
            "stored_effects": len(raw),
            "sha256": hashlib.sha256(db.read_bytes()).hexdigest()
        })
    assert sorted(x["case"] for x in verified) == sorted(captured[i][:-7] for i in range(7))
    report = {
        "schema": "preserved-original-checkpoint-sql-v1",
        "status": "PASS",
        "source_blob_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "cases": sorted(verified, key=lambda row: row["case"])
    }
    (out / "retained-sql-audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("PRESERVED_SQL", json.dumps({"status": "PASS", "cases": len(verified),
        "effects": sum(row["stored_effects"] for row in verified)}))

if __name__ == "__main__":
    main()
