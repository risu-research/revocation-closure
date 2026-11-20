#!/usr/bin/env python3
"""Rebuild the fixed policy and audit both HTTP/SQLite recipients."""
from pathlib import Path
import hashlib,json,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
EXPECTED=json.loads((ROOT/'expected_results.json').read_text())

def run(script,*args):
    print('RUN',script,*map(str,args),flush=True)
    subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],cwd=ROOT,check=True)

def read(path):return json.loads((OUT/path).read_text())

OUT.mkdir(exist_ok=True)
for name in ('stage_s_baseline_rerun','a0_enforced_primary'):
    p=OUT/name
    if p.exists():shutil.rmtree(p)
run('src/build_a0_ir.py')
assert hashlib.sha256((ROOT/'inputs/a0_typed_policy.json').read_bytes()).hexdigest()==EXPECTED['inputs']['typed_policy_sha256']
run('src/a0_assurance.py')
run('stage_s_original/code/run.py','--out',OUT/'stage_s_baseline_rerun')
run('stage_s_original/code/independent_audit.py',OUT/'stage_s_baseline_rerun')
run('stage_s_hardened/code/run.py','--out',OUT/'a0_enforced_primary')
run('stage_s_hardened/code/independent_audit.py',OUT/'a0_enforced_primary')
for name,key in (('stage_s_baseline_rerun','baseline'),('a0_enforced_primary','with_policy_check')):
    s=read(name+'/summary.json');want=EXPECTED[key]
    assert (s['attempts'],s['persisted'],s['oracle_unsafe_persisted'])==(want['attempts'],want['physical_writes'],want['oracle_unsafe_writes']),(name,s,want)
run('tests/compare_original_stage_s.py')
comparison=read('baseline_to_stage_t_comparison.json')
assert comparison['legitimate_persisted_original']==comparison['legitimate_persisted_stage_t']==8
run('tests/test_a0_integration.py')
mutations=read('a0_mutation_results.json')['totals'];want=EXPECTED['mutations']
assert (mutations['injected_mutations'],mutations['detected_by_compiler'],mutations['mutations_tested_against_recipient'],mutations['mutated_protected_source_writes_persisted'],mutations['mutated_clean_source_writes_preserved']) == (want['policy_mutations_detected'],want['policy_mutations_detected'],want['real_http_mutations'],want['protected_writes_persisted'],want['clean_writes_preserved']),(mutations,want)
run('tests/test_sql_tamper_detection.py')
assert read('a0_sql_tamper_test.json')['separate_auditor_rejected']
print('PASS: fixed policy, both independent SQL audits, 13 mutation checks, and tamper rejection')
