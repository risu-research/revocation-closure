#!/usr/bin/env python3
"""Compare a fresh separately audited recipient study with recorded outcomes."""
from pathlib import Path
import json, subprocess, sys, hashlib
R=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2: raise SystemExit('Usage: python tests/check_public_reproduction.py <fresh-output-directory>')
out=Path(sys.argv[1]).resolve()
expected=json.loads((R/'recorded_outcomes.json').read_text())
saved=json.loads((out/'study_summary.json').read_text())
for key, value in expected.items():
    if key == 'missed_notice_unsafe_effects':continue
    assert saved[key]==value,(key,saved[key],value)
pr=subprocess.run([sys.executable,str(R/'tests/independent_audit.py'),str(out)],cwd=R,capture_output=True,text=True)
assert pr.returncode==0,(pr.stdout[-500:],pr.stderr[-500:])
audit=json.loads(pr.stdout.split('INDEPENDENT_STAGE_R_AUDIT ',1)[1])
assert audit['status']=='PASS'
assert audit['deliberate_unsafe_missed_notice_effects']==expected['missed_notice_unsafe_effects']
assert audit['signed_case_events_checked']==15
assert audit['clock_assertions_checked']==17
assert audit['persisted_signed_q_outputs']==5
print('PASS: fresh recipient SQL, signed actor events, deadline checks, and missed-notice control')
