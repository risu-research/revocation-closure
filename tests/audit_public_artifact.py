#!/usr/bin/env python3
"""Read-only audit of tracked public research files. Standard library only."""
import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+['\"][^'\"]+['\"])?\)")
BAD_FILES = {".env", ".env.local", "id_rsa", "id_ed25519"}
BAD_SUFFIXES = {".pem", ".key", ".p8", ".p12", ".pfx", ".sqlite", ".db"}
SIGNALS = {
    "access-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{28,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "cloud-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "api-secret": re.compile(r"\bsk-[A-Za-z0-9_-]{28,}\b"),
    "private-signing-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "personal-email": re.compile(r"\b[A-Za-z0-9._%+-]+@(?:gmail|hotmail|outlook|yahoo|protonmail|web)\.[A-Za-z]{2,}\b", re.I),
    "local-user-directory": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\\\s]+|/Users/[^/\s]+/(?:Desktop|Downloads)|/home/" + "oai/|/mnt/" + "data/"),
}
def rows(name):
    with (ROOT / ("experiments/court_coding/" + name)).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def court_audit(errors):
    original = rows("frozen_520.csv")
    final = rows("conditional_520.csv")
    edits = rows("adjudicated_changes_120.csv")
    before = {(x["order_id"], x["code"]): int(x["original_value"]) for x in original}
    after = {(x["order_id"], x["code"]): int(x["conditional"]) for x in final}
    changes = {(x["order_id"], x["code"]): x for x in edits}
    diff = {k for k in before if before[k] != after.get(k)}
    actual = {
        "orders": len(rows("orders.csv")), "original_cells": len(original),
        "conditional_cells": len(final), "changed_cells": len(edits),
        "event_records": len(rows("event_predicates_40.csv")),
        "original_positives": sum(before.values()), "conditional_positives": sum(after.values()),
        "additions": sum(before[k] == 0 and after[k] == 1 for k in diff),
        "removals": sum(before[k] == 1 and after[k] == 0 for k in diff)
    }
    expected = {"orders": 40, "original_cells": 520, "conditional_cells": 520,
        "changed_cells": 120, "event_records": 40, "original_positives": 262,
        "conditional_positives": 378, "additions": 118, "removals": 2}
    if actual != expected or len(before) != 520 or len(after) != 520 or len(changes) != 120 or set(changes) != diff:
        errors.append({"rule": "court-record-reconciliation", "file": "experiments/court_coding"})
    for key, row in changes.items():
        if before.get(key) != int(row["original_value"]) or after.get(key) != int(row["adjudicated_value"]):
            errors.append({"rule": "court-record-join", "file": "experiments/court_coding", "cell": row["cell_key"]})
    return actual

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    tracked = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"]).split(b"\0")
    files = [ROOT / s.decode() for s in tracked if s]
    names = {p.relative_to(ROOT).as_posix() for p in files}
    errors, warnings = [], []
    md_count = py_count = local_links = 0
    for p in files:
        name = p.relative_to(ROOT).as_posix()
        if p.name in BAD_FILES or p.suffix.lower() in BAD_SUFFIXES:
            errors.append({"rule": "sensitive-file-type", "file": name})
        try:
            contents = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append({"rule": "nontext-file", "file": name})
            continue
        for rule, pattern in SIGNALS.items():
            if pattern.search(contents):
                errors.append({"rule": rule, "file": name})
        if p.suffix == ".py":
            py_count += 1
            try:
                compile(contents, name, "exec")
            except SyntaxError as e:
                errors.append({"rule": "python-syntax", "file": name, "line": e.lineno})
        if p.suffix.lower() != ".md":
            continue
        md_count += 1
        if re.search(r"manuscript remains unchanged|frozen submitted manuscript|camera-ready artifact scope will", contents, re.I):
            warnings.append({"rule": "stale-manuscript-status", "file": name})
        for m in LINK.finditer(contents):
            href = m.group(1).strip("<>")
            if href.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            href = unquote(href.split("#")[0].split("?")[0])
            if not href:
                continue
            local_links += 1
            target = (p.parent / href).resolve()
            try:
                path = target.relative_to(ROOT).as_posix()
            except ValueError:
                errors.append({"rule": "escaping-link", "file": name})
                continue
            if path not in names and not target.is_dir():
                errors.append({"rule": "broken-relative-link", "file": name, "target": path})
    try:
        court = court_audit(errors)
    except (KeyError, ValueError, OSError) as e:
        errors.append({"rule": "court-data-exception", "file": "experiments/court_coding", "type": type(e).__name__})
        court = {}
    report = {"schema": "public-artifact-static-audit-v1", "status": "FAIL" if errors else "PASS",
        "tracked_files": len(files), "compiled_python_files": py_count, "markdown_files": md_count,
        "checked_local_links": local_links, "court_coding": court,
        "errors": errors, "warnings": warnings}
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output)
    if errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
