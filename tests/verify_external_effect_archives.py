#!/usr/bin/env python3
"""Independent read-only checks of public Actions archives for the external-effect study.

Input: extracted original Actions artifact directory (dev or holdout). This script
reconstructs expected outcomes from the archived scenarios and stored SQL records.
It never imports the workflow runner, the receiver or the original SQL auditor.
"""
import argparse
import collections
import hashlib
import json
import sqlite3
from pathlib import Path

SCENARIOS = {
    'revoked_before_check', 'independent_clean', 'mixed_provenance',
    'revoke_after_client_check', 'clean_during_revocation', 'mixed_during_revocation',
    'missing_revoked_receipt', 'missing_clean_receipt', 'stale_revoked_digest',
    'stale_clean_digest', 'false_complete_clean_label',
    'false_complete_revoked_label', 'mixed_with_omitted_revoked',
    'revocation_withdrawn', 'prior_valid_authorization',
    'incomplete_mixed_receipt'
}
GUARDS = ('cached', 'client_precheck', 'sink_atomic')
ORDERS = ('acosta_notice', 'necec_challenge')
SEEDS = {'dev': tuple(range(901, 905)), 'holdout': tuple(range(7001, 7013))}


def digest(x):
    return hashlib.sha256(x.encode()).hexdigest()


def valid(receipt, payload):
    return (
        isinstance(receipt, dict)
        and receipt.get('complete') is True
        and receipt.get('payload_digest') == digest(payload)
        and isinstance(receipt.get('sources'), list)
        and bool(receipt['sources'])
        and all(s in ('R', 'K') for s in receipt['sources'])
    )


def check_dir(folder: Path, part: str):
    manifest = json.loads((folder / f'external_effect_{part}_oracle.json').read_text())
    acks = json.loads((folder / f'external_effect_{part}_acks.json').read_text())['acks']
    original = json.loads((folder / f'external_effect_{part}_audit.json').read_text())
    specs = manifest['cases']
    assert manifest['plan']['partition'] == part
    assert manifest['plan']['templates'] == 16
    assert len(specs) == len(SEEDS[part]) * 2 * 16 * 3
    assert len(acks) == len(specs) == original['cases']

    expected_keys = {
        (seed, order, scenario, guard)
        for seed in SEEDS[part]
        for order in ORDERS
        for scenario in SCENARIOS
        for guard in GUARDS
    }
    assert {(s['seed'], s['order'], s['scenario'], s['guard']) for s in specs} == expected_keys
    spec_by_id = {s['case_id']: s for s in specs}
    assert len(spec_by_id) == len(specs)
    ack_by_id = {a['case_id']: a for a in acks}
    assert len(ack_by_id) == len(specs) and ack_by_id.keys() == spec_by_id.keys()

    db = folder / ('effect-dev.sqlite' if part == 'dev' else 'effect-heldout.sqlite')
    c = sqlite3.connect(f'file:{db.resolve()}?mode=ro', uri=True)
    c.execute('PRAGMA query_only=ON')
    assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    policies = {
        cid: (rev, epoch)
        for cid, rev, epoch in c.execute('SELECT case_id,revoked,epoch FROM policies')
    }
    receipts = {
        cid: json.loads(v) if v is not None else None
        for cid, v in c.execute('SELECT case_id,value FROM receipts')
    }
    histories = collections.defaultdict(list)
    for cid, epoch, revoked in c.execute(
        'SELECT case_id,epoch,revoked FROM policy_events ORDER BY case_id,epoch'
    ):
        histories[cid].append((epoch, revoked))
    writes = collections.defaultdict(list)
    for wid, cid, payload, api, epoch in c.execute(
        'SELECT id,case_id,payload,entrypoint,epoch FROM writes ORDER BY id'
    ):
        writes[cid].append((wid, payload, api, epoch))
    decisions = collections.defaultdict(list)
    for cid, api, verdict, epoch in c.execute(
        'SELECT case_id,api,verdict,epoch FROM decisions ORDER BY id'
    ):
        decisions[cid].append((api, verdict, epoch))

    assert spec_by_id.keys() == policies.keys() == receipts.keys() == histories.keys()
    assert spec_by_id.keys() == decisions.keys()
    assert set(writes).issubset(set(spec_by_id))
    by_guard = {g: collections.Counter() for g in GUARDS}
    by_scenario = collections.defaultdict(collections.Counter)
    audit_by_id = {r['case_id']: r for r in original['rows']}
    assert audit_by_id.keys() == spec_by_id.keys()

    for cid, s in spec_by_id.items():
        g = s['guard']
        schedule = s['policy_schedule']
        receipt = s['receipt']
        payload = s['payload']
        true_sources = s['oracle_sources']
        assert true_sources and set(true_sources) <= {'R', 'K'}
        assert receipts[cid] == receipt
        assert cid == digest(
            f"opaque:{s['order']}:{s['seed']}:{s['scenario']}:{g}"
        )[:32]
        assert payload == digest(
            f"payload:{s['order']}:{s['seed']}:{s['scenario']}"
        )[:48]

        history = {
            'before': [(0, 0), (1, 1)],
            'race': [(0, 0), (1, 1)],
            'release': [(0, 0), (1, 1), (2, 0)],
            'none': [(0, 0)],
        }[schedule]
        assert histories[cid] == history
        assert policies[cid] == (history[-1][1], history[-1][0])
        is_valid = valid(receipt, payload)
        lists_R = is_valid and 'R' in receipt['sources']

        if g == 'cached':
            expected = [('/write_unguarded', 'ALLOW', history[-1][0])]
        elif g == 'client_precheck':
            verdict = (
                'UNRESOLVED' if not is_valid else
                ('BLOCK' if lists_R and schedule == 'before' else 'ALLOW')
            )
            check_epoch = 1 if schedule == 'before' else 2 if schedule == 'release' else 0
            expected = [('authorize', verdict, check_epoch)]
            if verdict == 'ALLOW':
                expected.append(('/write_unguarded', 'ALLOW', history[-1][0]))
        else:
            verdict = (
                'UNRESOLVED' if not is_valid else
                ('BLOCK' if lists_R and history[-1][1] else 'ALLOW')
            )
            expected = [('/write_atomic', verdict, history[-1][0])]

        assert decisions[cid] == expected, (cid, s['scenario'], g, decisions[cid], expected)
        written = expected[-1][1] == 'ALLOW'
        assert len(writes[cid]) == int(written)
        if written:
            _, stored, api, epoch = writes[cid][0]
            assert stored == payload
            assert api == ('/write_atomic' if g == 'sink_atomic' else '/write_unguarded')
            assert epoch == history[-1][0]

        ack = ack_by_id[cid]
        assert ack['guard'] == g
        assert ack['replayed_historical_snapshot'] is True
        assert ack['latest_state_repaired'] is True
        assert ack['ack']['committed'] == written
        assert ack['ack']['verdict'] == expected[-1][1]

        source_R = 'R' in true_sources
        revoked = bool(history[-1][1])
        unsafe = written and source_R and revoked
        clean = not source_R
        race = unsafe and schedule == 'race'
        unresolved = any(d[1] == 'UNRESOLVED' for d in expected)
        counts = by_guard[g]
        counts['cases'] += 1
        counts['affected'] += int(source_R and revoked)
        counts['unsafe'] += int(unsafe)
        counts['clean'] += int(clean)
        counts['clean_committed'] += int(clean and written)
        counts['race_unsafe'] += int(race)
        counts['unresolved'] += int(unresolved)
        counts['writes'] += int(written)

        bucket = by_scenario[(g, s['scenario'])]
        bucket['cases'] += 1
        bucket['writes'] += int(written)
        bucket['unsafe'] += int(unsafe)
        bucket['unresolved'] += int(unresolved)
        audited = audit_by_id[cid]
        assert audited['observed_external_writes'] == int(written)
        assert audited['unauthorized_persisted_write'] == unsafe
        assert audited['independent_clean_effect_preserved'] == (clean and written)
        assert audited['observed_sql_epoch'] == history[-1][0]
        assert audited['true_revoked_source'] == source_R
        assert audited['revoked_at_commit'] == revoked

    total = sum(v['writes'] for v in by_guard.values())
    assert total == sum(len(v) for v in writes.values())
    assert total == original['physical_persisted_writes']
    for g, counts in by_guard.items():
        earlier = original['by_guard'][g]
        for ours, recorded in (
            ('cases', 'cases'),
            ('affected', 'revoked_at_commit'),
            ('unsafe', 'unsafe_writes'),
            ('clean', 'clean_cases'),
            ('clean_committed', 'clean_writes_preserved'),
            ('race_unsafe', 'race_unsafe'),
            ('unresolved', 'abstentions'),
        ):
            assert counts[ours] == earlier[recorded], (part, g, ours)
    assert len(by_scenario) == 16 * 3
    c.close()

    return {
        'partition': part,
        'checks': len(specs),
        'database_sha256': hashlib.sha256(db.read_bytes()).hexdigest(),
        'original_audit_sha256': hashlib.sha256(
            (folder / f'external_effect_{part}_audit.json').read_bytes()
        ).hexdigest(),
        'sql_integrity': 'ok',
        'by_guard': {g: dict(v) for g, v in by_guard.items()},
        'by_guard_template': {
            f'{g}/{scenario}': dict(v)
            for (g, scenario), v in sorted(by_scenario.items())
        },
        'total_writes': total,
        'status': 'PASS',
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dev', type=Path, required=True)
    ap.add_argument('--holdout', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    results = {
        'dev': check_dir(args.dev, 'dev'),
        'holdout': check_dir(args.holdout, 'holdout'),
    }
    if args.out:
        args.out.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')
    for split, report in results.items():
        print(split, report['checks'], report['total_writes'], report['by_guard'])
