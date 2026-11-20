#!/usr/bin/env python3
"""Run frozen-source policy scoring and inspect separately persisted write effects."""
from pathlib import Path
import hashlib, json, subprocess, sys, sqlite3, tempfile, shutil
R = Path(__file__).resolve().parents[1]

def run(*args, check=True):
    p = subprocess.run([sys.executable, *map(str, args)], cwd=R, text=True, capture_output=True)
    if check and p.returncode: raise AssertionError((args, p.stdout[-1000:], p.stderr[-1000:]))
    return p

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

for manifest_name in ['gold/FROZEN_SHA256.json', 'gold/FROZEN_SCENARIOS_SHA256.json']:
    for rel, expected in json.loads((R/manifest_name).read_text()).items():
        assert sha(R/rel) == expected, rel
seal=json.loads((R/'confirmatory/SEAL_BEFORE_GENERATION.json').read_text())
assert sha(R/'src/generic_policy_extractor.py') == seal['frozen_extractor_sha256']
for rel in ('new_gold.csv', 'new_order_passages.json'):
    assert sha(R/'confirmatory'/rel) == seal[rel]

saved_a=json.loads((R/'results/one_shot_policy_proposals.json').read_text())
saved_b=json.loads((R/'confirmatory/one_shot_proposals.json').read_text())
saved_score=json.loads((R/'results/extraction_scored.json').read_text())['summary']
saved_confirm=json.loads((R/'confirmatory/confirmatory_score.json').read_text())['summary']

with tempfile.TemporaryDirectory(prefix='order_transfer_test_') as tmp:
    tmp=Path(tmp)
    first=tmp/'first.json'
    third=tmp/'third.json'
    run('src/generic_policy_extractor.py', '--source', 'sources/scoped_order_passages.json','--out',first)
    run('src/generic_policy_extractor.py', '--source', 'confirmatory/new_order_passages.json','--out',third)
    assert json.loads(first.read_text()) == saved_a
    assert json.loads(third.read_text()) == saved_b
    assert json.loads(run('src/score_frozen_holdout.py').stdout)['complete_tuple_correct']==saved_score['complete_tuple_correct']==3
    assert json.loads(run('confirmatory/score_code_frozen.py').stdout)['full_tuples_correct']==saved_confirm['full_tuples_correct']==0
    assert saved_score['gold_duties']==20 and saved_score['action_detected']==13
    assert saved_confirm['gold_duties']==8 and saved_confirm['action_detected']==0

    work=tmp/'effects'
    run('src/run_effect_study.py', '--output',work)
    audit=json.loads(run('src/independent_effect_auditor.py','--folder',work).stdout)
    by={m['mode']:m for m in audit['results']}
    assert (by['static']['attempts'],by['static']['false_allow'],by['static']['physical_effects'])==(18,11,18)
    assert (by['gated']['attempts'],by['gated']['false_allow'],by['gated']['physical_effects'])==(18,2,9)
    assert by['gated']['false_allow_ids']==['DB06','LV04']

    # Modify a physical SQL effect row on a disposable copy. The auditor must reject it.
    copy=tmp/'tampered'
    shutil.copytree(work,copy)
    with sqlite3.connect(copy/'gated/recipient.sqlite') as db:
        tables=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        # Force a changed effect payload, preserving the audit oracle and runner records.
        assert 'effects' in tables,tables
        cols=[row[1] for row in db.execute('PRAGMA table_info(effects)')]
        col='content_sha256' if 'content_sha256' in cols else 'content'
        db.execute(f"UPDATE effects SET {col}=? WHERE rowid=(SELECT min(rowid) FROM effects)",('TAMPERED',))
    bad=run('src/independent_effect_auditor.py','--folder',copy,check=False)
    assert bad.returncode!=0,'Tampered persisted effect was accepted'

print('PASS: 20 original duties, 8 frozen-order duties, 36 SQL requests, and SQL tamper rejection')
