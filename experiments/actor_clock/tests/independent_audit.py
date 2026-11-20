"""Read-only audit of preserved Stage R SQLite, written independently of recipient.
Rechecks Ed25519 envelopes, Q source/output identity, actor roles, trusted dates,
selected deadline math, and the physical effect rows from archived snapshots.
"""
from __future__ import annotations
import argparse,base64,calendar,csv,datetime as dt,hashlib,json,sqlite3,sys
from collections import Counter
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

ROOT=Path(__file__).resolve().parents[1]
EVENT_ROLES={'producer_notice':'producing_party','receipt_of_log_and_replacement':'receiving_challenger',
'final_termination':'court_event_attester','return_or_destruction':'receiving_party','self_discovery':'receiving_party',
'producer_log_delivered':'producing_party','challenge_filed':'receiving_challenger','written_confirmation':'receiving_counsel'}
TEST_HOLIDAYS={'2026-11-26','2026-12-25'}

def stable(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def sigcheck(pem,tok,fields=None):
    assert isinstance(tok,dict) and set(tok)=={'body','signature'}
    body=tok['body'];assert isinstance(body,dict)
    if fields is not None:assert set(body)==fields,(set(body)^fields)
    pub=serialization.load_pem_public_key(pem.encode())
    pub.verify(bytes.fromhex(tok['signature']),stable(body).encode('utf-8'))
    return body

def due(day:str,n:int,unit:str):
    x=dt.date.fromisoformat(day)
    if unit=='calendar_days':return (x+dt.timedelta(days=n)).isoformat()
    if unit=='months':
        m=x.month-1+n;y=x.year+m//12;m=m%12+1
        return dt.date(y,m,min(x.day,calendar.monthrange(y,m)[1])).isoformat()
    assert unit=='business_days'
    count=0
    while count<n:
        x+=dt.timedelta(days=1)
        if x.weekday()<5 and x.isoformat() not in TEST_HOLIDAYS:count+=1
    return x.isoformat()

def audit(results:Path):
    trust=json.loads((results/'public_trust.json').read_text())
    events=json.loads((results/'event_results.json').read_text())
    snapshots=json.loads((results/'duty_snapshots.json').read_text())
    sessions=json.loads((results/'session_metadata.json').read_text())
    summary=json.loads((results/'study_summary.json').read_text())
    duties=list(csv.DictReader((ROOT/'source_stage_n'/'R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER.csv').open()))
    assert len(duties)==8
    assert len(sessions)==summary['sessions']==6
    known_q={p.name.removesuffix('_evidence.json'):json.loads(p.read_text())
             for p in (ROOT/'source_stage_q').glob('*_evidence.json')}
    event_ok=0;effect_ok=0;attestations=0;clock_ok=0;archives=0;challenges=0;effect_by_session={};late=[]
    for s in sessions:
        name=s['name'];dbpath=results/(name+'_effects.sqlite')
        assert sha(dbpath.read_bytes())==s['sqlite_sha256']
        db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        ev=list(db.execute('SELECT event_id,case_id,event_name,source_id,actor_role,sequence,received_date,policy_epoch,envelope FROM legal_events ORDER BY rowid'))
        attempts=list(db.execute('''SELECT id,case_id,artifact_id,role,verdict,persisted,policy_epoch,clock_date,sources,reason,
                 proof_sha256,policy_digest,bundle_json,actor_envelope_json,declared_sources_json,client_cached_approval
                 FROM legal_effect_attempts ORDER BY id'''))
        effects=list(db.execute('SELECT attempt_id,case_id,artifact_id,payload_sha256,policy_epoch,clock_date FROM legal_effects ORDER BY id'))
        stored_archives=list(db.execute('SELECT case_id,note_id,qualified_counsel_attested,policy_epoch,reuse_blocked,actor_envelope_json,trusted_facts_digest FROM legal_archive'))
        copies=list(db.execute('SELECT case_id,source_id,challenge_role,reserved_epoch,reserved_date,restriction,actor_envelope_json FROM legal_challenge_copy'))
        assert len(copies)==s['challenge_copies']
        noticed=set();seq_seen={};by_events={};by_event_actors={}
        for evid,case,evname,src,role,seq,received,epoch,toktext in ev:
            body=sigcheck(trust['role_pubkeys'][case][role],json.loads(toktext),
                  {'schema','event_id','case','event','source_id','role','sequence','nonce'})
            assert body['schema']=='case-actor-event-v1'
            assert body['event_id']==evid and body['event']==evname and body['role']==role
            assert body['case']==case and body['source_id']==src and body['sequence']==seq
            assert EVENT_ROLES[evname]==role
            prev=seq_seen.get((case,role),0);assert seq>prev;seq_seen[(case,role)]=seq
            dt.date.fromisoformat(received)
            by_events.setdefault((case,evname),[]).append((received,epoch))
            by_event_actors[evid]=body
            if evname in ('producer_notice','self_discovery'):
                assert (case,src) in {(r[0],r[1]) for r in trust['pinned_source_digests']}
                noticed.add((case,src,epoch))
                original=db.execute('SELECT notice_id,case_id,source_id,epoch,signed_envelope FROM notices WHERE notice_id=?',(evid,)).fetchone()
                assert original==(evid,case,src,epoch,toktext)
            event_ok+=1
        assert len(ev)==s['events']
        assert len(attempts)==s['effect_attempts']
        assert len(effects)==s['effect_rows']
        assert len(stored_archives)==s['archives']
        actual_effects={r[0]:r for r in effects}
        saw_attempts=set();persisted=0
        for (id,case,artifact,role,verdict,stored,epoch,date,source_json,reason,
             proofsha,poldig,bundletext,actortext,declaredtext,cached) in attempts:
            assert id not in saw_attempts;saw_attempts.add(id)
            bundle=json.loads(bundletext);actor=json.loads(actortext);claimed=json.loads(declaredtext)
            assert sha(stable({'bundle':bundle,'actor':actor,'claimed':claimed}).encode())==proofsha
            assert poldig==db.execute('SELECT policy_digest FROM legal_effect_attempts WHERE id=?',(id,)).fetchone()[0]
            assert date>= '2026-11-19'
            rows=actual_effects.get(id)
            assert int(rows is not None)==stored
            assert int(verdict=='ALLOW_SCOPED')==stored
            assert stored in (0,1)
            if stored:
                ab=sigcheck(trust['role_pubkeys'][case][role],actor,
                            {'schema','case','artifact_id','action','role','nonce'})
                assert ab['schema']=='actor-effect-authorization-v1'
                assert (ab['case'],ab['artifact_id'],ab['role'],ab['action'])==(case,artifact,role,'EXTERNAL_EFFECT')
                assert role in {'receiving_party','receiving_counsel'}
                assert bundle==known_q[next(k for k,v in known_q.items() if v==bundle)],'not frozen stage Q bundle'
                old=bundle['legacy_seal'];new=bundle['execution_attestation']
                ob=sigcheck(trust['broker_public_key_pem'],old,
                            {'schema','run_id','artifact_id','case','kind','output_sha256','closed','events'})
                nb=sigcheck(trust['broker_public_key_pem'],new,
                            {'schema','run_id','artifact_id','case','kind','program_sha256','launcher_sha256',
                             'output_sha256','observed_event_count','events_sha256','legacy_seal_sha256',
                             'worker_uid','broker_uid','sandbox_profile'})
                assert ob['closed'] is True and ob['artifact_id']==artifact and ob['case']==case
                assert nb['program_sha256'] in trust['approved_program_sha256']
                assert nb['launcher_sha256']==trust['launcher_sha256']
                assert nb['sandbox_profile']=='uid-dac-no-new-privs-seccomp-deny-v1'
                assert (nb['worker_uid'],nb['broker_uid'])==(23321,23322)
                for key in ('case','artifact_id','run_id','output_sha256','kind'):assert ob[key]==nb[key]
                assert nb['legacy_seal_sha256']==sha(stable(old).encode())
                assert nb['events_sha256']==sha(stable(ob['events']).encode())
                assert nb['observed_event_count']==len(ob['events'])
                output=base64.b64decode(bundle['output_b64'],validate=True)
                assert sha(output)==ob['output_sha256']==nb['output_sha256']==rows[3]
                assert any(sha(p.read_bytes())==nb['program_sha256'] for p in (ROOT/'vendor_stage_q'/'programs').glob('*.py'))
                resolved=set()
                for idx,read in enumerate(ob['events'],1):
                    assert set(read)=={'seq','type','id','source_sha256'} and read['seq']==idx
                    if read['type']=='source':
                        exp=db.execute('SELECT source_sha256 FROM sources WHERE case_id=? AND source_id=?',(case,read['id'])).fetchone()
                        assert exp and exp[0]==read['source_sha256']
                        resolved.add(read['id'])
                    elif read['type']=='parent':
                        parent=db.execute('SELECT case_id,resolved_sources FROM artifacts WHERE artifact_id=?',(read['id'],)).fetchone()
                        assert parent and parent[0]==case;resolved.update(json.loads(parent[1]))
                    else:raise AssertionError('Invalid read type')
                resolved.update(r[0] for r in db.execute('SELECT source_id FROM sources WHERE case_id=? AND source_sha256=?',(case,ob['output_sha256'])))
                assert sorted(resolved)==sorted(claimed)==json.loads(source_json)
                # Stronger oracle: effect must have no LOCALLY acknowledged source notice or final-covered material.
                asof_noticed={(c,source) for c,source,notice_epoch in noticed if notice_epoch<=epoch}
                assert not any((case,source) in asof_noticed for source in resolved)
                final_in_effect=any(c==case and en=='final_termination' and ep<=epoch for (c,en),lst in by_events.items() for _,ep in lst)
                assert not (final_in_effect and any(trust['source_classifications'][case].get(source)=='covered_final' for source in resolved))
                assert rows[1:3]==(case,artifact) and rows[4:6]==(epoch,date)
                persisted+=1;attestations+=1
            effect_ok+=1
        effect_by_session[name]=persisted
        assert persisted==len(effects)
        for case,source,role,epoch,date,restriction,tok in copies:
            b=sigcheck(trust['role_pubkeys'][case][role],json.loads(tok),
                 {'schema','case','artifact_id','action','role','nonce'})
            assert case=='iottie' and role=='receiving_challenger'
            assert b['action']=='CHALLENGE_COPY' and b['artifact_id']==source and b['case']==case
            assert restriction=='COURT_CHALLENGE_ONLY_NO_EXTERNAL_USE'
            assert any(c==case and src==source and notice_epoch<=epoch for c,src,notice_epoch in noticed)
            challenges+=1
        for case,note,qual,epoch,reuse,token,ff in stored_archives:
            frozen=trust['archive_classifications'][case][note]
            assert frozen['qualified'] and frozen['contains_specified'] is False
            assert ff==sha(stable(frozen).encode())
            assert qual==reuse==1
            b=sigcheck(trust['role_pubkeys'][case]['receiving_counsel'],json.loads(token),
                {'schema','case','artifact_id','action','role','nonce'})
            assert b['schema']=='actor-effect-authorization-v1' and b['action']=='ARCHIVE'
            assert b['artifact_id']==note and b['role']=='receiving_counsel'
            assert any(c==case and ev=='final_termination' and ep<=epoch for (c,ev),v in by_events.items() for _,ep in v)
            archives+=1
        db.close()
    for e in events:
        assert e['actual']['status']==e['expected']
        if e['expected']=='REJECTED':
            assert e['actual']['reason']
    assert effect_by_session['missed_notice']==1 # Deliberately unsafe outside the recipient local view
    for s in snapshots:
        if 'duty' not in s:continue
        d=s['duty']
        if d['unit']=='business_days' and s['status']=='UNRESOLVED_CALENDAR':
            assert s['due'] is None
        else:
            assert s['due']==due(s['duty']['start'],d['amount'],d['unit'])
        assert s['actor']==d['actor'] and s['trigger']==d['trigger']
        clock_ok+=1
    assert summary['persisted_sql_effect_rows']==sum(effect_by_session.values())
    assert summary['persisted_sql_effect_rows']==5
    assert archives==3 and challenges==1
    assert effect_ok==summary['external_effect_requests']==17
    assert clock_ok==summary['verified_clock_snapshots']-3==17
    result={'status':'PASS','sessions':len(sessions),'signed_case_events_checked':event_ok,
            'effects_and_denials_audited':effect_ok,'persisted_signed_q_outputs':attestations,
            'physical_effects_by_suite':effect_by_session,'restricted_archives_checked':archives,'restricted_challenge_copies_checked':challenges,
            'clock_assertions_checked':clock_ok,'deliberate_unsafe_missed_notice_effects':1,
            'scope':'Independent read-only checking of archived SQL signatures and data, not legal-compliance adjudication.'}
    (results/'independent_stage_r_audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('INDEPENDENT_STAGE_R_AUDIT',json.dumps(result,sort_keys=True))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('result_dir',nargs='?',default='results');args=p.parse_args()
    audit(Path(args.result_dir).resolve())
