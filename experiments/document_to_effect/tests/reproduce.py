"""Run the complete local replay and verify the saved evaluation totals."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
results = root / 'results'
results.mkdir(exist_ok=True)
python = sys.executable
expected = json.loads((root / 'recorded' / 'expected.json').read_text())

with tempfile.TemporaryDirectory(prefix='replay_', dir=results) as scratch:
    out = Path(scratch)
    subprocess.run([python, str(root / 'code' / 'run.py'), '--out', str(out)], cwd=root, check=True, capture_output=True, text=True)
    actual = json.loads((out / 'summary.json').read_text())
    if actual != expected:
        raise AssertionError(f'Unexpected replay totals: {actual}')
    report = subprocess.run([python, str(root / 'code' / 'independent_audit.py'), str(out)], cwd=root, check=True, capture_output=True, text=True)
    audit = json.loads(report.stdout)
    required = {
        'status': 'PASS',
        'attempts': 46,
        'actual_source_reads': 18,
        'signed_permits': 38,
        'signed_actor_events': 7,
        'writes_physically_persisted': 17,
        'oracle_unsafe_writes': 9,
    }
    for key, value in required.items():
        if audit.get(key) != value:
            raise AssertionError(f'Independent audit mismatch for {key}: {audit.get(key)} != {value}')
    print('PASS 46 requests, 17 persisted writes, 9 unsafe controls, independent SQL audit')
