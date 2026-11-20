"""Independent, read-only Stage Q auditor.

Does not import the worker, broker, recipient or policy compiler implementation.
Checks Ed25519 seals, source/code/output/event binding, owner notices, and real
SQLite rows. It also runs independent proof-tamper negative controls.
"""
import base64, copy, hashlib, json, sqlite3, sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def check_sig(pub,env):
    assert isinstance(env,dict) and set(env)=={'body','signature'}
    pub.verify(bytes.fromhex(env['signature']),canon(env['body']))
    return env['body']

def audit(root, results_folder='results'):
    results=root/results_folder
    summary=json.loads((results/'stage_q_result.json').read_text())
    anchors=json.loads((results/'public_trust.json').read_text())
    broker=serialization.load_pem_public_key(anchors['broker_public_key_pem'].encode())
    owner={k:serialization.load_pem_public_key(v.encode()) for k,v in anchors['owner_pubs'].items()}
    assert summary['status']=='PASS'
    pinned={(case,sid):digest for case,sid,digest in anchors['pinned_source_digests']}
    assert len(pinned)==6
    db=sqlite3.connect('file:'+str(results/'recipient_snapshot.sqlite')+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    db_sources={(r[0],r[1]):r[2] for r in db.execute('SELECT case_id,source_id,source_sha256 FROM sources')}
    assert db_sources==pinned
    notices=[r for r in db.execute('SELECT notice_id,case_id,source_id,owner_sequence,epoch,signed_envelope FROM notices ORDER BY epoch')]
    assert len(notices)==3 and [x[4] for x in notices]==[1,2,3]
    for noticeid,case,sid,sequence,epoch,envelope in notices:
        body=check_sig(owner[case],json.loads(envelope))
        assert (body['notice_id'],body['case'],body['source_id'],body['sequence'])==(noticeid,case,sid,sequence)
        assert body['event']=='C_PRIV_NOTICE' and (case,sid) in pinned
    assert db.execute('SELECT epoch FROM policy_epoch').fetchone()==(3,)
    att_rows=[r for r in db.execute('SELECT artifact_id,run_id,case_id,kind,output_sha256,resolved_sources,broker_seal FROM artifacts')]
    artifact_by_id={r[0]:r for r in att_rows}
    approve_literal=bool(summary.get('approve_literal',False))
    assert len(artifact_by_id)==(12 if approve_literal else 11)
    verified=[]
    valid_bundles={}
    for job in summary['programs']:
        pth=root/'programs'/job['program']
        assert pth.exists() and sha(pth.read_bytes())==job['sha256']
        assert job['runner_uid']==23321 and job['broker_uid']==23322
        if not job['sealed']:
            assert job['worker_rc']!=0 and job['broker_rc']!=0
            assert not (results/(job['name']+'_evidence.json')).exists()
            continue
        assert job['worker_rc']==0 and job['broker_rc']==0
        bundle=json.loads((results/job['bundle_file']).read_text())
        assert bundle['schema']=='trusted-transform-bundle-v1'
        output=base64.b64decode(bundle['output_b64'],validate=True)
        old=check_sig(broker,bundle['legacy_seal'])
        new=check_sig(broker,bundle['execution_attestation'])
        assert old['schema']=='broker-observed-reads-v1' and new['schema']=='broker-run-code-binding-v1'
        assert new['program_sha256']==sha(pth.read_bytes())
        assert new['launcher_sha256']==anchors['launcher_sha256']==sha((root/'experiments/trusted_transform/runner.py').read_bytes())
        assert new['sandbox_profile']=='uid-dac-no-new-privs-seccomp-deny-v1'
        assert new['worker_uid']==23321 and new['broker_uid']==23322
        assert old['closed'] is True
        for k in ('run_id','artifact_id','case','kind','output_sha256'):
            assert new[k]==old[k]
        assert old['output_sha256']==sha(output)
        assert new['events_sha256']==sha(canon(old['events']))
        assert new['legacy_seal_sha256']==sha(canon(bundle['legacy_seal']))
        assert new['observed_event_count']==len(old['events'])>0
        resolved=set()
        for i,event in enumerate(old['events'],1):
            assert set(event)=={'seq','type','id','source_sha256'} and event['seq']==i
            if event['type']=='source':
                assert pinned[(old['case'],event['id'])]==event['source_sha256']
                resolved.add(event['id'])
            elif event['type']=='parent':
                assert event['source_sha256'] is None
                pr=artifact_by_id[event['id']]
                assert pr[2]==old['case']
                resolved.update(json.loads(pr[5]))
            else:raise AssertionError('Unknown event type')
        if job['name']=='literal_launder':
            # An unapproved program may embed source text in its own code while
            # legitimately reading a clean source. Valid proof, rejected effect.
            assert (old['artifact_id'] in artifact_by_id)==approve_literal
            assert set(resolved)=={'iottie_CLEAN'}
            assert b'SYNTHETIC_PRIV_SOURCE_FOR_iottie_V1_03' in output
            assert (job['sha256'] in anchors['approved_program_sha256'])==approve_literal
            if approve_literal:
                row=artifact_by_id[old['artifact_id']]
                assert row[4]==old['output_sha256'] and set(json.loads(row[5]))==resolved
        else:
            row=artifact_by_id[old['artifact_id']]
            assert row[1:5]==(old['run_id'],old['case'],old['kind'],old['output_sha256'])
            assert set(json.loads(row[5]))==resolved
            assert json.loads(row[6])==bundle['legacy_seal']
            assert job['sha256'] in anchors['approved_program_sha256']
        valid_bundles[job['name']]=bundle
        verified.append(job['name'])
    assert len(verified)==12
    # Prove independent evaluator rejects tampered proof forms, not just the suite's own expected strings.
    clean=valid_bundles['clean_hash']; tamper_tests={}
    for name in ('output','program','events','legacy_seal'):
        bad=copy.deepcopy(clean)
        if name=='output':bad['output_b64']=base64.b64encode(b'fake').decode()
        elif name=='program':bad['execution_attestation']['body']['program_sha256']='f'*64
        elif name=='events':bad['legacy_seal']['body']['events'][0]['id']='iottie_PRIV'
        elif name=='legacy_seal':bad['legacy_seal']['signature']='00'*64
        try:
            old=check_sig(broker,bad['legacy_seal'])
            new=check_sig(broker,bad['execution_attestation'])
            assert new['output_sha256']==sha(base64.b64decode(bad['output_b64']))
            assert new['events_sha256']==sha(canon(old['events']))
        except (InvalidSignature,AssertionError,ValueError):
            tamper_tests[name]='REJECTED'
        else:raise AssertionError('Failed to reject '+name)
    effects=[r for r in db.execute('''SELECT e.artifact_id,e.policy_epoch,e.output_sha256,a.verdict,a.resolved_sources,a.persisted
                FROM effects e JOIN attempts a ON a.attempt_id=e.attempt_id ORDER BY e.effect_id''')]
    assert len(effects)==(5 if approve_literal else 4)
    expected_ids=['PRE_REVERSE','CLEAN_HASH','CAMM_CLEAN_TRANSFORM','NAPOLI_CLEAN_TRANSFORM']
    if approve_literal:expected_ids.append('LITERAL_LAUNDER')
    assert [r[0] for r in effects]==expected_ids
    for aid,epoch,dig,verdict,source_json,persisted in effects:
        assert verdict=='ALLOW_SCOPED' and persisted==1
        assert dig==artifact_by_id[aid][4]
        if epoch>0:
            assert not any(src in {n[2] for n in notices if n[1]==artifact_by_id[aid][2]}
                           for src in json.loads(source_json))
    if approve_literal:
        evidence=valid_bundles['literal_launder']
        assert evidence['legacy_seal']['body']['events'][0]['id']=='iottie_CLEAN'
        assert b'SYNTHETIC_PRIV_SOURCE_FOR_iottie_V1_03' in base64.b64decode(evidence['output_b64'])
        matched=[r for r in effects if r[0]=='LITERAL_LAUNDER']
        assert len(matched)==1 and matched[0][1]==3 and json.loads(matched[0][4])==['iottie_CLEAN']
    attempts=[r for r in db.execute('SELECT artifact_id,verdict,persisted,policy_epoch,resolved_sources FROM attempts ORDER BY attempt_id')]
    assert len(attempts)==(13 if approve_literal else 12) and sum(r[2] for r in attempts)==(5 if approve_literal else 4)
    assert [r[1] for r in attempts]==['ALLOW_SCOPED','BLOCK','ALLOW_SCOPED','BLOCK','BLOCK','BLOCK',
                                      'ALLOW_SCOPED','BLOCK','ALLOW_SCOPED']+(['ALLOW_SCOPED'] if approve_literal else [])+['BLOCK','HOLD','HOLD']
    rejections=list(db.execute('SELECT artifact_id,proof_sha256,reason,policy_epoch FROM execution_rejections'))
    assert len(rejections)==(4 if approve_literal else 5) and all(r[3]==3 for r in rejections)
    assert sum(r[0]=='LITERAL_LAUNDER' for r in rejections)==(0 if approve_literal else 1)
    assert any('not in recipient-approved' in r[2] for r in rejections)==(not approve_literal)
    assert len({r[1] for r in rejections})==(4 if approve_literal else 5)
    assert [v['status'] for v in summary['recipient_decisions']]==['ALLOW_SCOPED','BLOCK','ALLOW_SCOPED',
                                      'BLOCK','BLOCK','BLOCK','ALLOW_SCOPED','BLOCK','ALLOW_SCOPED',('ALLOW_SCOPED' if approve_literal else 'HOLD'),'BLOCK',
                                      'HOLD','HOLD','HOLD','HOLD','HOLD','HOLD']
    assert sum(not j['sealed'] for j in summary['programs'])==5
    db.close()
    answer={'schema':'stage-q-independent-audit-v1','status':'PASS',
        'verified_signed_job_count':len(verified),'verified_job_names':verified,
        'rejected_exec_without_seal':5,'tamper_controls':tamper_tests,
        'verified_broker_source_index':len(pinned),'verified_owner_notices':len(notices),
        'physical_attempt_rows':len(attempts),'physical_execution_rejections':len(rejections),
        'approval_ablation':approve_literal,'physical_effect_rows':len(effects),'allowed_effect_ids':[e[0] for e in effects],
        'limitations':['Independent audit verifies recorded data and signatures, not completeness against a malicious host root.',
                       'Broker attestation measures a program delivered to runner, not formal proof of exact instruction history.',
                       'Kernel syscall behavior is evidenced by rejected job exit status and broker receipt, not re-executed by auditor.']}
    (results/'independent_audit.json').write_text(json.dumps(answer,indent=2,sort_keys=True)+'\n')
    print('INDEPENDENT_STAGE_Q',json.dumps({k:v for k,v in answer.items() if k not in ('limitations','verified_job_names')},sort_keys=True))
    return answer

if __name__=='__main__':
    audit(Path(sys.argv[1]) if len(sys.argv)>1 else Path('.'), sys.argv[2] if len(sys.argv)>2 else 'results')
