#!/usr/bin/env python3
"""Reproduce 520 order-wide labels from the public frozen matrix and 120 author adjudications."""
from pathlib import Path
from collections import Counter
import csv

BASE=Path(__file__).resolve().parent

def load(name):
    with (BASE/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

frozen=load('frozen_520.csv')
changes=load('adjudicated_changes_120.csv')
snapshot=load('conditional_520.csv')
open_checks=load('source_checks_pending.csv')
assert (len(frozen),len(changes),len(snapshot),len(open_checks))==(520,120,520,5)
original={}
for r in frozen:
    key=(int(r['order_id']),r['code'])
    assert key not in original
    original[key]=(r['case'],int(r['original_value']))
assert len(original)==520
revisions={}
for r in changes:
    key=(int(r['order_id']),r['code'])
    assert key in original and key not in revisions
    assert r['case']==original[key][0] and int(r['original_value'])==original[key][1]
    assert r['cell_key']==f'{key[0]:02d}-{key[1]}'
    assert r['source_url'].startswith('https://') and r['source_clause'] and r['coding_reason']
    before,after=int(r['original_value']),int(r['adjudicated_value'])
    assert before in (0,1) and after==1-before
    assert r['change']==f'{before}->{after}'
    revisions[key]=r
assert Counter(x['review_route'] for x in changes)=={
    'core_conflict':74,'core_shared_miss':2,
    'supplementary_conflict':42,'supplementary_shared_miss':2}
assert Counter(x['change'] for x in changes)=={'0->1':118,'1->0':2}
assert {(int(x['order_id']),x['code']) for x in changes if x['remaining_source_verification']}=={(17,'BK'),(17,'CERT'),(18,'BK'),(18,'CERT'),(21,'DB')}
assert {x['cell_key'] for x in open_checks}=={x['cell_key'] for x in changes if x['remaining_source_verification']}
conditional={k:(int(revisions[k]['adjudicated_value']) if k in revisions else v[1]) for k,v in original.items()}
assert sum(v[1] for v in original.values())==262 and sum(conditional.values())==378
assert sum(a!=b[1] for a,b in zip([conditional[k] for k in original],original.values()))==120
assert sorted(k for k in revisions if original[k][1]==1)==[(10,'DER'),(21,'DB')]
assert len({(int(x['order_id']),x['code']) for x in snapshot})==520
for r in snapshot:
    key=(int(r['order_id']),r['code']);before=original[key][1];after=conditional[key]
    assert r['case']==original[key][0]
    assert int(r['original'])==before and int(r['conditional'])==after
    assert int(r['changed'])==int(before!=after)
    assert r['cell_key']==f'{key[0]:02d}-{key[1]}'
    assert r['review_route']==(revisions[key]['review_route'] if key in revisions else '')
    assert r['source_clause']==(revisions[key]['source_clause'] if key in revisions else '')
    assert r['source_url']==(revisions[key]['source_url'] if key in revisions else '')
    assert r['source_check']==('OPEN' if key in revisions and revisions[key]['remaining_source_verification'] else '')
expected={'SRC':(40,40),'COPY':(39,40),'USE':(34,39),'TP':(23,32),'NOTE':(21,39),'SUM':(14,34),'DER':(6,12),'DB':(7,8),'AI':(11,12),'BK':(6,32),'CERT':(16,38),'PART':(11,13),'CHAL':(34,39)}
for code,(a,b) in expected.items():
    assert sum(v[1] for k,v in original.items() if k[1]==code)==a
    assert sum(v for k,v in conditional.items() if k[1]==code)==b
assert sum(int(x['order_id'])<=30 for x in changes)==76
print('PASS 40 orders x 13 codes, 520 original cells and 120 mapped revisions')
print('PASS 118 additions, 2 removals, 262 original and 378 conditional positives')
print('PASS 13 code frequency pairs, 76 core and 44 supplementary changes')
print('PASS 5 historical source-verification flags preserved')
