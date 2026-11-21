#!/usr/bin/env python3
"""Independent bounded retrospective source-candidate audit on original tool-read archive.

Uses only stdlib, SQLite opened read-only, the archived oracle/acknowledgement/audit
files, the pinned two synthetic source values and the documented transform.
Does not import the experiment runner or original auditor. Outputs per-case results.
"""
from __future__ import annotations
import argparse, collections, hashlib, itertools, json, sqlite3
from pathlib import Path

SOURCES = {'R':'SYNTHETIC_REVOKED_DISCOVERY_RECORD_V1',
           'K':'SYNTHETIC_INDEPENDENT_LEGAL_RECORD_V1'}
ORIGINAL_HASHES = {
 'dev': {'evidence.sqlite':'49f55ac3bb9225c3576343930984e7f62bb6d5ce5171c0b3afb4f90157b10250',
         'tool_read_dev_audit.json':'e85e13673070647fbcc705c73983ff560bbc7ed4fa41cab4b2c1554581190b42',
         'tool_read_dev_oracle.json':'cb142b75ee9e10eb2f7ed1d77d7df94d1b9980e87c797a02c762b8e9fdc8b739'},
 'holdout': {'evidence.sqlite':'b9ce256fd295be2fb1f762b0f89ba22706af6a736e14ac528e7911b0577001cd',
         'tool_read_holdout_audit.json':'48308343845dda0cfd07efd128cd4f9bc012797ee441d5689b18514d2f089a6a',
         'tool_read_holdout_oracle.json':'bd760ac328617610ea6fba1a2e64d7a345c37b8f0642c7601b2b7de4bd6c6d75'}
}

def sha(s): return hashlib.sha256(s.encode('utf8')).hexdigest()
def dfile(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def transformed(sequence, nonce, sources):
    vals=[sources[x] for x in sequence]
    return sha(json.dumps(vals,sort_keys=True,separators=(',',':'))+'::'+nonce)

def recover(stored_transform_digest, nonce, candidates, limit=2):
    """Find every candidate sequence whose registered transform digest matches."""
    if not isinstance(nonce,str) or len(nonce)!=32 or any(x not in '0123456789abcdef' for x in nonce):
        return {'status':'UNRESOLVED_NONCE','matches':[]}
    names=sorted(candidates)
    matches=[]
    for n in range(1,limit+1):
        for candidate in itertools.product(names,repeat=n):
            output=transformed(candidate,nonce,candidates)
            if sha(output)==stored_transform_digest:
                matches.append({'sources':list(candidate),'recomputed_output':output})
    return {'status':'UNIQUE' if len(matches)==1 else 'UNRESOLVED_NO_MATCH' if not matches else 'UNRESOLVED_AMBIGUOUS', 'matches':matches}

def audit_partition(root,part):
    for name,want in ORIGINAL_HASHES[part].items():
        got=dfile(root/name)
        assert got==want, (part,name,got,want)
    oracle=json.loads((root/f'tool_read_{part}_oracle.json').read_text())
    original=json.loads((root/f'tool_read_{part}_audit.json').read_text())
    ack=json.loads((root/f'tool_read_{part}_acks.json').read_text())
    plans=oracle['specs']
    byack={a['flow_id']:a for a in ack['replies']}
    byoriginal={x['id']:x for x in original['rows']}
    assert len(byack)==len(byoriginal)==len(plans)==original['cases']
    db=sqlite3.connect('file:'+str((root/'evidence.sqlite').resolve())+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    transforms={f:(i,d,n,nonce) for i,f,d,n,nonce in db.execute('SELECT id,flow_id,output_digest,observed_read_count,nonce FROM transforms')}
    observed=collections.defaultdict(list)
    for i,f,source,h in db.execute('SELECT id,flow_id,source,content_digest FROM source_reads ORDER BY id'):
        assert h==sha(SOURCES[source]);observed[f].append(source)
    effects=collections.defaultdict(list)
    for i,f,out,mode,epoch in db.execute('SELECT id,flow_id,output,mode,epoch FROM effects ORDER BY id'):
        effects[f].append({'id':i,'output':out,'mode':mode,'epoch':epoch})
    dec={f:(mode,verdict,epoch) for i,f,mode,verdict,epoch in db.execute('SELECT id,flow_id,mode,verdict,epoch FROM decisions')}
    assert len(transforms)==len(dec)==len(plans)
    stats=collections.Counter(); by_scenario=collections.defaultdict(collections.Counter)
    per=[]
    for c in plans:
        flow=c['flow_id'];scenario=c['scenario'];guard=c['guard']
        assert flow in byoriginal and flow in byack
        tid,registered_digest,observed_count,nonce=transforms[flow]
        observed_truth=[s for s in c['sources'] if s not in c['untracked']]
        assert observed[flow]==observed_truth and observed_count==len(observed_truth)
        full=recover(registered_digest,nonce,SOURCES)
        without_r=recover(registered_digest,nonce,{'K':SOURCES['K']})
        assert full['status']=='UNIQUE' and full['matches'][0]['sources']==c['sources'],(part,scenario,guard,full)
        assert without_r['status']==('UNIQUE' if 'R' not in c['sources'] else 'UNRESOLVED_NO_MATCH'),(part,scenario,guard,without_r)
        output=full['matches'][0]['recomputed_output']
        assert sha(output)==registered_digest
        record=effects[flow]
        assert len(record)<=1
        if record:
            assert record[0]['mode']==guard
        assert bool(record)==(dec[flow][1]=='ALLOW')
        assert byack[flow]['historical_snapshot_replayed'] is True
        assert byack[flow]['latest_state_repaired'] is True
        assert byoriginal[flow]['registered_output_sha256']==registered_digest
        assert byoriginal[flow]['source_ids_oracle']==c['sources']
        assert byoriginal[flow]['nonce']==nonce
        assert byoriginal[flow]['actual_stored_writes']==len(record)
        matches_stored=(len(record)==1 and record[0]['output']==output)
        tampered_committed=(len(record)==1 and not matches_stored)
        if record:
            assert record[0]['output']==(output+':tampered' if c['fault']=='tamper' else output)
        if tampered_committed: assert c['fault']=='tamper' and guard in ('cached','declared')
        if scenario=='untraced_revoked':
            assert not observed[flow] and c['sources']==['R']
        if scenario=='partial_bypass_revoked':
            assert observed[flow]==['K'] and c['sources']==['K','R']
        stats['cases']+=1
        stats['full_unique']+=int(full['status']=='UNIQUE')
        stats['without_r_unique']+=int(without_r['status']=='UNIQUE')
        stats['without_r_unresolved']+=int(without_r['status'].startswith('UNRESOLVED'))
        stats['actual_sql_writes']+=len(record)
        stats['tamper_controls']+=int(c['fault']=='tamper')
        stats['physically_tampered_writes']+=int(tampered_committed)
        stats['fully_unlogged_revoked']+=int(scenario=='untraced_revoked')
        stats['partial_bypass_mixed']+=int(scenario=='partial_bypass_revoked')
        stats['fully_unlogged_clean']+=int(scenario=='untraced_clean')
        stats['observed_read_events']+=len(observed[flow])
        stats['actual_tool_calls']+=len(c['sources'])
        by_scenario[scenario]['cases']+=1
        by_scenario[scenario]['without_r_unique']+=int(without_r['status']=='UNIQUE')
        by_scenario[scenario]['actual_sql_writes']+=len(record)
        by_scenario[scenario]['physically_tampered_writes']+=int(tampered_committed)
        per.append({'flow_id':flow,'scenario':scenario,'guard':guard,'seed':c['seed'],'fixture':c['order'],
                    'oracle_sources':c['sources'],'logged_sources':observed[flow],
                    'registered_hash':registered_digest,'nonce':nonce,
                    'recovered_sources':full['matches'][0]['sources'],
                    'full_status':full['status'],'missing_R_status':without_r['status'],
                    'stored_effect_exists':bool(record),'stored_effect_matches_reconstruction': matches_stored,
                    'physically_tampered_write':tampered_committed})
    # Tests of missing/ambiguous evidence, using a real archived single-R case.
    example=next(p for p in plans if p['sources']==['R'])
    _,h,_,nonce=transforms[example['flow_id']]
    controls={
      'missing_nonce':recover(h,None,SOURCES)['status'],
      'obsolete_R_snapshot':recover(h,nonce,{'R':'OBSOLETE_SOURCE_R','K':SOURCES['K']})['status'],
      'no_R_snapshot':recover(h,nonce,{'K':SOURCES['K']})['status'],
      'duplicate_identity':recover(h,nonce,{'R':SOURCES['R'],'R_ALIAS':SOURCES['R'],'K':SOURCES['K']})['status']
    }
    assert controls=={'missing_nonce':'UNRESOLVED_NONCE','obsolete_R_snapshot':'UNRESOLVED_NO_MATCH',
                      'no_R_snapshot':'UNRESOLVED_NO_MATCH','duplicate_identity':'UNRESOLVED_AMBIGUOUS'}
    expect={'dev': {'cases':180,'full_unique':180,'without_r_unique':84,'without_r_unresolved':96,
                    'actual_sql_writes':120,'tamper_controls':12,'physically_tampered_writes':8,
                    'fully_unlogged_revoked':12,'partial_bypass_mixed':12,'fully_unlogged_clean':12,
                    'observed_read_events':180,'actual_tool_calls':216},
            'holdout': {'cases':540,'full_unique':540,'without_r_unique':252,'without_r_unresolved':288,
                    'actual_sql_writes':360,'tamper_controls':36,'physically_tampered_writes':24,
                    'fully_unlogged_revoked':36,'partial_bypass_mixed':36,'fully_unlogged_clean':36,
                    'observed_read_events':540,'actual_tool_calls':648}}
    assert stats==expect[part],(part,stats,expect[part])
    assert original['physical_writes']==stats['actual_sql_writes']
    db.close()
    return {'partition':part,'original_sha256':ORIGINAL_HASHES[part],
            'totals':dict(sorted(stats.items())),'by_scenario':{k:dict(v) for k,v in sorted(by_scenario.items())},
            'evidence_controls':controls,'rows':per,'passed':True}

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--dev',type=Path,required=True)
    a.add_argument('--holdout',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    opt=a.parse_args()
    data={'schema':'r32-posthoc-recovery-audit-v1',
          'source':'Original recorded tool-read Actions archives; bounded candidate replay with retained nonce and registered hash',
          'results':{'development':audit_partition(opt.dev,'dev'),
                     'heldout':audit_partition(opt.holdout,'holdout')}}
    opt.out.parent.mkdir(parents=True,exist_ok=True)
    opt.out.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    for key,rec in data['results'].items():print('PASS',key,json.dumps(rec['totals'],sort_keys=True),rec['evidence_controls'])
