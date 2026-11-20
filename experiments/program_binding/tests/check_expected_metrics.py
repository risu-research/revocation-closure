import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
expected = json.loads((root / 'recorded_outcomes.json').read_text())
for directory, name in [('fresh_baseline', 'baseline'), ('fresh_ablation', 'approved_literal_ablation')]:
    p = root / directory
    if not p.exists():
        raise SystemExit(f'Missing run: {directory}. Follow README reproduction commands.')
    r = json.loads((p / 'stage_q_result.json').read_text())
    a = json.loads((p / 'independent_audit.json').read_text())
    d = [x['status'] for x in r['recipient_decisions']]
    actual = {
        'signed_completions': sum(bool(x['sealed']) for x in r['programs']),
        'unsigned_execution_failures': sum(not bool(x['sealed']) for x in r['programs']),
        'recipient_decisions': len(d),
        'allowed': d.count('ALLOW_SCOPED'),
        'blocked': d.count('BLOCK'),
        'held': d.count('HOLD'),
        'persisted_effects': a['physical_effect_rows'],
        'tampered_proof_rejections': sum(v == 'REJECTED' for v in a['tamper_controls'].values()),
    }
    assert actual == expected[name], (name, actual, expected[name])
    assert a['status'] == 'PASS'
    print('PASS', name, actual)
