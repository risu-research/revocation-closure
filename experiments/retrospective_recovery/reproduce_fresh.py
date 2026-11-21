#!/usr/bin/env python3
"""Independently recover candidate sources from freshly produced tool-read traces.

The historical auditor pins the original database hashes. New trials have fresh
nonces and fresh SQLite files, so this entry point binds the independent auditor
to the new file hashes before applying exactly the same per-case assertions.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import audit_retrospective_recovery as audit

REQUIRED = ('evidence.sqlite', 'tool_read_{part}_oracle.json',
            'tool_read_{part}_audit.json', 'tool_read_{part}_acks.json')

def verify(root: Path, part: str) -> dict:
    expected = {name.format(part=part): audit.dfile(root / name.format(part=part))
                for name in REQUIRED}
    audit.ORIGINAL_HASHES[part] = expected
    record = audit.audit_partition(root, part)
    assert record['passed'] and record['totals']['cases'] == (180 if part == 'dev' else 540)
    return record

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--dev', type=Path, required=True)
    p.add_argument('--holdout', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    opt = p.parse_args()
    result = {'schema': 'retrospective-recovery-fresh-v1',
              'method': 'six candidate sequences with recorded nonce and independent SQL audit',
              'results': {'development': verify(opt.dev, 'dev'),
                          'heldout': verify(opt.holdout, 'holdout')}}
    opt.out.parent.mkdir(parents=True, exist_ok=True)
    opt.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    for label, value in result['results'].items():
        print('PASS', label, json.dumps(value['totals'], sort_keys=True))

if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Run the independent audit with Python assertions enabled.')
    main()
