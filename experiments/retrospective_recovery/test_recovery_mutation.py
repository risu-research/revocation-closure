#!/usr/bin/env python3
"""Two negative controls on disposable SQLite copies, independent of archive hashes."""
import argparse
import importlib.util
import shutil
import sqlite3
import tempfile
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--dev',type=Path,required=True,help='Extracted development _runs/dev directory')
a=p.parse_args()
audit=Path(__file__).with_name('audit_retrospective_recovery.py')
spec=importlib.util.spec_from_file_location('audit_r32',audit)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
src=a.dev.resolve()
with tempfile.TemporaryDirectory(prefix='r32-negative-') as d:
    dest=Path(d)/'dev'
    shutil.copytree(src,dest)
    with sqlite3.connect(dest/'evidence.sqlite') as con:
        effect_id=con.execute("SELECT id FROM effects WHERE mode='cached' AND output NOT LIKE '%:tampered' ORDER BY id LIMIT 1").fetchone()[0]
        con.execute('UPDATE effects SET output=? WHERE id=?',('INJECTED_CORRUPT_BODY',effect_id))
    m.ORIGINAL_HASHES['dev']['evidence.sqlite']=m.dfile(dest/'evidence.sqlite')
    rejected=False
    try:m.audit_partition(dest,'dev')
    except AssertionError:rejected=True
    assert rejected,'Unexpected acceptance of changed physical SQL body'
    print('PASS: changed physical effect rejected by per-row auditor')
    shutil.copy2(src/'evidence.sqlite',dest/'evidence.sqlite')
    with sqlite3.connect(dest/'evidence.sqlite') as con:
        transform_id=con.execute('SELECT id FROM transforms ORDER BY id LIMIT 1').fetchone()[0]
        con.execute('UPDATE transforms SET output_digest=? WHERE id=?',('0'*64,transform_id))
    m.ORIGINAL_HASHES['dev']['evidence.sqlite']=m.dfile(dest/'evidence.sqlite')
    rejected=False
    try:m.audit_partition(dest,'dev')
    except AssertionError:rejected=True
    assert rejected,'Unexpected acceptance of changed transform registration'
    print('PASS: changed registration rejected by candidate-matching audit')
