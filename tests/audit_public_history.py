#!/usr/bin/env python3
"""Audit reachable Git history for private artifacts and credentials without logging values."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNALS = {
    "access-token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9_]{28,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "cloud-token": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "api-key": re.compile(rb"\bsk-[A-Za-z0-9_-]{28,}\b"),
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "personal-contact": re.compile(rb"\b[A-Za-z0-9._%+-]+@(?:gmail|hotmail|outlook|yahoo|protonmail|web)\.[A-Za-z]{2,}\b", re.I),
    "local-personal-path": re.compile(rb"[A-Za-z]:\\Users\\[^\\\s]+\\|/home/" + b"oai/|/mnt/" + b"data/"),
}
BAD_FILES = {".env", ".env.local", "id_rsa", "id_ed25519"}
BAD_SUFFIXES = {".pem", ".key", ".p8", ".p12", ".pfx", ".sqlite", ".db", ".tex", ".pdf", ".docx", ".zip"}

def git(*args):
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    assert git("rev-parse", "--is-shallow-repository").strip() == b"false", \
        "Audit requires fetch-depth: 0"
    named = {}
    for line in git("rev-list", "--objects", "--all").splitlines():
        parts = line.split(b" ", 1)
        if len(parts) == 2 and parts[1]:
            sha = parts[0].decode()
            name = parts[1].decode("utf-8", "replace")
            named.setdefault(sha, set()).add(name)
    issues = []
    count = 0
    for sha, paths in sorted(named.items()):
        if git("cat-file", "-t", sha).strip() != b"blob":
            continue
        count += 1
        content = git("cat-file", "-p", sha)
        for path in sorted(paths):
            if Path(path).name in BAD_FILES or Path(path).suffix.lower() in BAD_SUFFIXES:
                issues.append({
                    "rule": "historical-sensitive-artifact-type",
                    "path": path, "blob_sha": sha
                })
        for rule, pattern in SIGNALS.items():
            matches = list(pattern.finditer(content))
            if rule == "local-personal-path":
                def is_regex_definition(match):
                    start = content.rfind(b"\n", 0, match.start()) + 1
                    end = content.find(b"\n", match.end())
                    line = content[start:end if end >= 0 else len(content)]
                    return b"re.compile(" in line and (
                        b'"personal-path"' in line or
                        b'"local-personal-path"' in line
                    )
                matches = [m for m in matches if not is_regex_definition(m)]
            if matches:
                issues.append({
                    "rule": rule, "paths": sorted(paths), "blob_sha": sha
                })
    report = {
        "schema": "git-public-history-audit-v1",
        "status": "FAIL" if issues else "PASS",
        "named_git_objects": len(named),
        "unique_blobs_scanned": count,
        "issues": issues,
    }
    content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
    print(content)
    if issues:
        sys.exit(1)

if __name__ == "__main__":
    main()
