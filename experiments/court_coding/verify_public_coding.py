#!/usr/bin/env python3
"""Check the published original and event-specific court-order aggregates."""
import csv, hashlib, json
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parent

def load(name):
    with (ROOT/name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))

orders=load('orders.csv')
labels=load('frozen_520.csv')
codebook=load('codebook.csv')
pins=load('source_clause_pins.csv')
disputed=load('reviewed_disagreements_77.csv')
events=load('event_predicates_40.csv')
assert len(orders)==40 and {int(x['order_id']) for x in orders}==set(range(1,41))
assert sum(x['stratum']=='core_clawback' for x in orders)==30
assert all(x['public_docket_url'].startswith('https://') for x in orders)
codes={x['code'] for x in codebook}
assert len(codes)==13
assert len(labels)==520
assert len({(x['order_id'], x['code']) for x in labels})==520
assert {x['code'] for x in labels}==codes
assert all(x['original_value'] in ('0','1') for x in labels)
core=Counter(x['code'] for x in labels if int(x['order_id'])<=30 and x['original_value']=='1')
expected={'NOTE':21,'TP':18,'SUM':12,'CERT':12,'PART':11,'DB':7,'DER':5,'AI':4,'BK':4}
assert all(core[k]==v for k,v in expected.items()),(core,expected)
assert len(pins)==47 and len({x['order_id'] for x in pins})==27
assert len(disputed)==77 and all(1<=int(x['order_id'])<=30 for x in disputed)
assert sum(x['changed']=='1' for x in disputed)==74
assert len({(x['order_id'], x['code']) for x in disputed})==77
assert len(events)==40
assert {x['order_id'] for x in events}=={x['order_id'] for x in orders}
checks={
    'notes_order_wide':(30,39,'1'),
    'direct_privilege_note_action':(21,23,'YES_EXPLICIT'),
    'final_archive_exception':(19,28,'YES_EXPLICIT'),
    'active_certification':(29,38,'1'),
    'written_certification':(22,30,'1'),
    'counsel_archive':(22,32,'1'),
    'system_backup':(8,13,'1'),
}
for col,(expect_core,expect_all,positive) in checks.items():
    assert sum(r[col]==positive for r in events)==expect_all,(col,'all')
    assert sum(r[col]==positive for r in events if r['stratum']=='core_clawback')==expect_core,(col,'core')
manifest=json.loads((ROOT/'manifest.json').read_text())
for name,m in manifest['files'].items():
    p=ROOT/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'],name
    assert len(load(name))==m['rows_excluding_header'],name
print('PASS 40 orders, 520 frozen labels, 47 clause pins, 77 reviewed disagreements, 40 event records')
print('PASS original core frequencies and seven event-specific core/all-40 frequencies')
