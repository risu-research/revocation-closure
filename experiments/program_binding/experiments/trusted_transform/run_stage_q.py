"""Stage Q: arbitrary Python transforms behind broker-owned source and recipient effect boundaries.

Runs real Linux UIDs and libseccomp. Disposable container only; requires EUID 0.
Outputs only synthetic artifacts and a copied read-only SQLite recipient DB.
"""
from __future__ import annotations
import argparse,base64,copy,hashlib,json,os,shutil,signal,socket,sqlite3,stat,subprocess,sys,tempfile,time
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from experiments.enforced_custody.ipc import client
from experiments.policy_compiler.verified_recipient import sign_notice

WORKER_UID=23321;BROKER_UID=23322;RECIPIENT_UID=23323

def transition(uid):
    def setup():
        import ctypes
        libc=ctypes.CDLL(None,use_errno=True)
        if libc.prctl(38,1,0,0,0):raise OSError(ctypes.get_errno(),'no_new_privs')
        os.setgroups([]);os.setresgid(uid,uid,uid);os.setresuid(uid,uid,uid)
        os.umask(0o077)
    return setup

def makedir(p,uid,mode=0o700,gid=None):
    p.mkdir();os.chown(p,uid,uid if gid is None else gid);os.chmod(p,mode)

def create_file(p,data,uid,mode=0o600):
    p.write_bytes(data);os.chown(p,uid,uid);os.chmod(p,mode)

def ready(p,proc,timeout=15):
    limit=time.monotonic()+timeout
    while time.monotonic()<limit:
        if p.exists():return
        if proc.poll() is not None:
            out,err=proc.communicate(timeout=2)
            raise RuntimeError('Recipient startup failed: '+err.decode(errors='replace')[-2500:])
        time.sleep(.04)
    raise TimeoutError('Recipient startup timeout')

def run(a):
    if os.geteuid()!=0 or sys.platform!='linux':
        raise RuntimeError('Requires disposable Linux with root in the namespace')
    root=Path(tempfile.mkdtemp(prefix='stage_q_priv_',dir='/tmp'))
    os.chmod(root,0o711)
    base=Path(__file__).resolve().parents[2]
    programs=base/'programs'
    env=os.environ.copy()
    env['PYTHONPATH']=str(base);env['PYTHONDONTWRITEBYTECODE']='1'
    for k in list(env):
        if any(s in k.upper() for s in ('TOKEN','PASSWORD','SECRET','API_KEY','AUTH','CREDENTIAL')):
            env.pop(k,None)
    procs=[]; jobs=[];recipient_res=[]
    try:
        vault=root/'vault';broker_out=root/'broker_out';runner_home=root/'runner_home';recipient_home=root/'recipient_home';ipc=root/'recipient_ipc'
        makedir(vault,BROKER_UID);makedir(broker_out,BROKER_UID);makedir(runner_home,WORKER_UID)
        makedir(recipient_home,RECIPIENT_UID);makedir(ipc,RECIPIENT_UID,0o2750,WORKER_UID)
        sources={};pins=[]
        for case in ('iottie','camm','napoli'):
            for label in ('PRIV','CLEAN'):
                sid=f'{case}_{label}'
                raw=(f'SYNTHETIC_{label}_SOURCE_FOR_{case}_V1_03').encode()
                filename=f'{case}_{label.lower()}.dat'
                create_file(vault/filename,raw,BROKER_UID)
                sources[sid]={'case':case,'filename':filename,'sha256':hashlib.sha256(raw).hexdigest()}
                pins.append((case,sid,sources[sid]['sha256']))
        create_file(vault/'index.json',(json.dumps(sources,sort_keys=True)+'\n').encode(),BROKER_UID)
        broker_key=Ed25519PrivateKey.generate()
        private=broker_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption())
        pub=broker_key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        create_file(vault/'broker_private.pem',private,BROKER_UID)
        owner_keys={case:Ed25519PrivateKey.generate() for case in ('iottie','camm','napoli')}
        owner_pubs={case:key.public_key().public_bytes(serialization.Encoding.PEM,
                   serialization.PublicFormat.SubjectPublicKeyInfo).decode() for case,key in owner_keys.items()}
        launcher_hash=hashlib.sha256((base/'experiments/trusted_transform/runner.py').read_bytes()).hexdigest()
        approved_files=('reverse_bytes.py','clean_hash.py','concat_sources.py','parent_transform.py',
                        'camm_summary.py','camm_clean.py','napoli_analysis.py','napoli_clean.py',
                        'sidechannel_attack.py') # deliberate output-channel control
        if a.approve_literal:
            approved_files += ('literal_launder.py',)
        approved_hashes=[hashlib.sha256((programs/name).read_bytes()).hexdigest() for name in approved_files]
        cfg={'owner_pub':owner_pubs,'pinned_sources':pins,'launcher_sha256':launcher_hash,
             'approved_program_sha256':approved_hashes}
        create_file(recipient_home/'trust.json',(json.dumps(cfg,sort_keys=True)+'\n').encode(),RECIPIENT_UID)
        create_file(recipient_home/'broker_pub.pem',pub,RECIPIENT_UID,0o600)
        recipient_socket=str(ipc/'recipient.sock')
        recipient_cmd=[sys.executable,'-m','experiments.trusted_transform.recipient_v2',
          '--socket',recipient_socket,'--broker-pubkey',str(recipient_home/'broker_pub.pem'),
          '--config',str(recipient_home/'trust.json'),'--db',str(recipient_home/'recipient.sqlite'),
          '--ready',str(ipc/'ready'),'--worker-uid',str(WORKER_UID),
          '--broker-uid',str(BROKER_UID),'--recipient-uid',str(RECIPIENT_UID)]
        recipient=subprocess.Popen(recipient_cmd,preexec_fn=transition(RECIPIENT_UID),
            cwd=str(base),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        procs.append(recipient);ready(ipc/'ready',recipient)
        def pair_job(name,program,case='iottie',kind='mixed_note',expected_success=True):
            a_sock,b_sock=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
            outfile=broker_out/(name+'.json')
            ruid=WORKER_UID;buid=BROKER_UID
            broker_cmd=[sys.executable,'-m','experiments.trusted_transform.broker_job',
                '--fd',str(a_sock.fileno()),'--vault',str(vault),'--program',str(programs/program),
                '--launcher',str(base/'experiments/trusted_transform/runner.py'),
                '--case',case,'--kind',kind,'--run-id','run_'+name,'--artifact-id',name.upper(),
                '--result',str(outfile),'--worker-uid',str(ruid),'--broker-uid',str(buid)]
            runner_cmd=[sys.executable,'-m','experiments.trusted_transform.runner',
                '--fd',str(b_sock.fileno()),'--uid',str(ruid)]
            bproc=subprocess.Popen(broker_cmd,pass_fds=(a_sock.fileno(),),preexec_fn=transition(buid),
                 cwd=str(base),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                 stdin=subprocess.DEVNULL)
            wproc=subprocess.Popen(runner_cmd,pass_fds=(b_sock.fileno(),),preexec_fn=transition(ruid),
                 cwd=str(runner_home),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                 stdin=subprocess.DEVNULL)
            a_sock.close();b_sock.close()
            try:
                wout,werr=wproc.communicate(timeout=12)
                bout,berr=bproc.communicate(timeout=12)
            except subprocess.TimeoutExpired:
                for p in (wproc,bproc):p.kill()
                wproc.communicate();bproc.communicate()
                raise RuntimeError('Job timeout: '+name)
            succeeded=(wproc.returncode==0 and bproc.returncode==0 and outfile.exists())
            if succeeded!=expected_success:
                raise AssertionError(f'Unexpected process outcome {name} worker={wproc.returncode} broker={bproc.returncode} stderr={berr[-1300:]!r}')
            rec={'name':name,'program':program,'sha256':hashlib.sha256((programs/program).read_bytes()).hexdigest(),
                 'worker_rc':wproc.returncode,'broker_rc':bproc.returncode,
                 'sealed':succeeded,'runner_uid':ruid,'broker_uid':buid,
                 'worker_stdout_len':len(wout), 'worker_stderr_len':len(werr)}
            if succeeded:
                rec['bundle']=json.loads(outfile.read_text())
                body=rec['bundle']['execution_attestation']['body']
                assert body['program_sha256']==rec['sha256']
                assert body['launcher_sha256']==launcher_hash
                assert body['output_sha256']==hashlib.sha256(base64.b64decode(rec['bundle']['output_b64'])).hexdigest()
                rec['observed_event_count']=body['observed_event_count']
            jobs.append(rec)
            return rec
        def attempt(row,claimed,expected,cached=False,bundle_override=None):
            bundle=bundle_override or row['bundle']
            got=client(recipient_socket,{'cmd':'attempt','bundle':bundle,'claimed_sources':claimed,
                                        'cached_approval':cached})
            if not got.get('ok'):raise AssertionError(got)
            d=got['result'];d['name']=row['name']
            if d['status']!=expected:raise AssertionError(f'{row["name"]} expected {expected} got {d}')
            recipient_res.append(d)
            return d
        first=pair_job('pre_reverse','reverse_bytes.py')
        attempt(first,['iottie_PRIV'],'ALLOW_SCOPED')
        notice_receipts=[]
        for case,key in owner_keys.items():
            notice=sign_notice(key,'notice_'+case,case,case+'_PRIV',1)
            got=client(recipient_socket,{'cmd':'notice','envelope':notice})
            if not got.get('ok'):raise AssertionError('Notice rejected '+str(got))
            notice_receipts.append({'case':case,'epoch':got['result']['epoch']})
        p=pair_job('post_reverse','reverse_bytes.py')
        attempt(p,[], 'BLOCK',cached=True) # intentional false clean claim
        clean=pair_job('clean_hash','clean_hash.py',kind='independent_note')
        attempt(clean,['iottie_CLEAN'],'ALLOW_SCOPED')
        mixed=pair_job('mixed_sources','concat_sources.py',kind='summary')
        attempt(mixed,[], 'BLOCK')
        parent=pair_job('parent_derived','parent_transform.py',kind='summary')
        attempt(parent,['iottie_PRIV','iottie_CLEAN'],'BLOCK')
        cp=pair_job('camm_priv_transform','camm_summary.py',case='camm',kind='summary')
        attempt(cp,[], 'BLOCK',cached=True)
        cc=pair_job('camm_clean_transform','camm_clean.py',case='camm',kind='summary')
        attempt(cc,['camm_CLEAN'],'ALLOW_SCOPED')
        np=pair_job('napoli_priv_transform','napoli_analysis.py',case='napoli',kind='mixed_note')
        attempt(np,[], 'BLOCK',cached=True)
        nc=pair_job('napoli_clean_transform','napoli_clean.py',case='napoli',kind='independent_note')
        attempt(nc,['napoli_CLEAN'],'ALLOW_SCOPED')
        # An arbitrary plugin can embed revoked bytes as a source-code literal and
        # read only CLEAN during execution. Its program digest is NOT approved.
        literal=pair_job('literal_launder','literal_launder.py',kind='mixed_note')
        attempt(literal,['iottie_CLEAN'],'ALLOW_SCOPED' if a.approve_literal else 'HOLD')
        side=pair_job('stdout_exfil','sidechannel_attack.py')
        attempt(side,['iottie_PRIV'],'BLOCK')
        assert side['worker_stdout_len']==0 and side['worker_stderr_len']==0
        # Missing source observations, intentional failures and malicious syscalls
        # never result in a broker-signed proof.
        for n,program in [('no_read','constant_no_read.py'),
                          ('vault_escape','direct_vault_attack.py'),
                          ('network_escape','network_attack.py'),
                          ('fork_escape','fork_attack.py'),
                          ('runtime_failure','exception_after_read.py')]:
            pair_job(n,program,expected_success=False)
        # Signature, output and code identity mutation: all must fail before any effect write.
        for name,mut in [('alter_output','output'),('alter_code_hash','program'),
                         ('alter_read_set','events'),('alter_legacy_seal','legacy')]:
            bun=copy.deepcopy(clean['bundle'])
            if mut=='output':bun['output_b64']=base64.b64encode(b'forged output').decode()
            elif mut=='program':bun['execution_attestation']['body']['program_sha256']='0'*64
            elif mut=='events':bun['legacy_seal']['body']['events'][0]['id']='iottie_PRIV'
            elif mut=='legacy':bun['legacy_seal']['signature']='00'*64
            label={'name':name}
            attempt(label,[], 'HOLD',bundle_override=bun)
        # Changing merely the claimed provenance on a signed clean result cannot upgrade it.
        attempt({'name':'replay_clean'},['iottie_CLEAN'],'HOLD',bundle_override=clean['bundle'],cached=True)
        # Brand-new clean proof, but conflicting client source list -> hold.
        fresh=pair_job('clean_conflict','clean_hash.py',kind='independent_note')
        attempt(fresh,[], 'HOLD')
        # v1-only submission cannot access recipient's v2-only route.
        rejected=client(recipient_socket,{'cmd':'attempt','bundle':{'schema':'broker-observed-reads-v1'},
            'claimed_sources':['iottie_CLEAN'],'cached_approval':True})
        assert rejected.get('ok') is False
        # Shut recipient down before independent disk inspection.
        recipient.terminate();recipient.communicate(timeout=5);procs.remove(recipient)
        dbpath=recipient_home/'recipient.sqlite'
        db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
        att=[dict(zip(('artifact_id','verdict','persisted','epoch','sources','reason'),row)) for row in db.execute(
            'SELECT artifact_id,verdict,persisted,policy_epoch,resolved_sources,reason FROM attempts ORDER BY attempt_id')]
        effects=[dict(zip(('artifact_id','epoch','digest'),row)) for row in db.execute(
            'SELECT artifact_id,policy_epoch,output_sha256 FROM effects ORDER BY effect_id')]
        rejections=[dict(zip(('artifact_id','proof_sha256','reason','epoch'),r)) for r in db.execute(
            'SELECT artifact_id,proof_sha256,reason,policy_epoch FROM execution_rejections ORDER BY rejection_id')]
        notices=db.execute('SELECT COUNT(*) FROM notices').fetchone()[0]
        rows_sources=db.execute('SELECT COUNT(*) FROM sources').fetchone()[0]
        db.close()
        assert notices==3 and rows_sources==6
        expected_ids=['PRE_REVERSE','CLEAN_HASH','CAMM_CLEAN_TRANSFORM','NAPOLI_CLEAN_TRANSFORM']
        if a.approve_literal: expected_ids.append('LITERAL_LAUNDER')
        assert [row['artifact_id'] for row in effects]==expected_ids,effects
        assert len(effects)==(5 if a.approve_literal else 4)
        assert effects[0]['epoch']==0 and all(r['epoch']==3 for r in effects[1:])
        assert all(row['verdict']!='ALLOW_SCOPED' for row in att if row['artifact_id'] not in tuple(expected_ids))
        assert len(att)==len([x for x in recipient_res if x['evidence_status'] not in ('INVALID_EXECUTION_PROOF','UNAPPROVED_PROGRAM')])
        assert len(rejections)==(4 if a.approve_literal else 5) and all(x['epoch']==3 for x in rejections)
        assert (any('not in recipient-approved' in x['reason'] for x in rejections)==(not a.approve_literal))
        assert not any(b'SYNTHETIC_PRIV_SOURCE' in x for x in [])
        # Save only public synthetic output, never broker private key/owner signing keys/runtime vault.
        out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
        shutil.copy2(dbpath,out/'recipient_snapshot.sqlite')
        trust={'broker_public_key_pem':pub.decode(),'owner_pubs':owner_pubs,
               'pinned_source_digests':pins,'launcher_sha256':launcher_hash,
               'approved_program_sha256':approved_hashes}
        (out/'public_trust.json').write_text(json.dumps(trust,sort_keys=True,indent=2)+'\n')
        public_jobs=[]
        for j in jobs:
            item={k:v for k,v in j.items() if k!='bundle'}
            if j['sealed']:
                pth=out/(j['name']+'_evidence.json')
                pth.write_text(json.dumps(j['bundle'],sort_keys=True,indent=2)+'\n')
                item['bundle_file']=pth.name
            public_jobs.append(item)
        summary={'schema':'stage-q-os-arbitrary-transform-v1','status':'PASS',
            'uids':{'broker':BROKER_UID,'runner':WORKER_UID,'recipient':RECIPIENT_UID},
            'constraint':'Linux DAC, non-root identities, no_new_privs, libseccomp denied open/socket/fork/exec; worker IPC through inherited socketpair',
            'programs':public_jobs,'recipient_decisions':recipient_res,'notices':notice_receipts,
            'db_attempts':att,'db_execution_rejections':rejections,'db_effects':effects,'trusted_source_count':rows_sources,
            'approve_literal':a.approve_literal,'effects_count':len(effects),'runner_stdout_capture':'no source bytes emitted to process stdout/stderr',
            'limits':['Arbitrary Python execution is bounded by tested process identity and syscall filter, not formal semantic verification.',
                      'The broker signs the measured PROGRAM BYTES delivered and output bytes observed, not proof of which instructions actually ran.',
                      'No independent cryptographic process-exit attestation is provided.',
                      'No full filesystem namespace, container-escape, host-root or covert-channel guarantee.',
                      'The broker has access to raw source bytes and may intentionally supply them through the documented read API.',
                      'Only a closed observation boundary is supported; pre-existing unrelated source copies or illicit inputs are outside scope.',
                      'The recipient checks effect-time policy in SQLite; it does not prove real deletion or compliance.']}
        (out/'stage_q_result.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
        print('STAGE_Q',json.dumps({'status':'PASS','signed_jobs':sum(j['sealed'] for j in jobs),
             'rejected_jobs':sum(not j['sealed'] for j in jobs),'attempts':len(att),'rejections':len(rejections),
             'persisted_effects':len(effects),'receipt_statuses':[x['status'] for x in recipient_res]},sort_keys=True))
        return summary
    finally:
        for p in procs:
            if p.poll() is None:p.kill()
            try:p.communicate(timeout=3)
            except Exception:pass
        shutil.rmtree(root,ignore_errors=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('results'))
    p.add_argument('--approve-literal',action='store_true',help='Allow the intentionally contaminated synthetic program for the controlled ablation')
    run(p.parse_args())
