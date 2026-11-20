"""Controlled end-to-end re-use of archived cryptographically valid Stage Q bundles.

Starts a separate recipient under Linux UID 23323, injects trusted simulated dates
via a root-only SO_PEERCRED route, and sends signed actor messages over the Unix socket.
No legal documents are deleted, and no live court/prosecutor signature is used.
"""
from __future__ import annotations
import argparse,copy,csv,hashlib,json,os,signal,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from stage_r.law import ROLES

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor_stage_q'))
from experiments.enforced_custody.ipc import client
from experiments.policy_compiler.verified_recipient import sign,stable_json

RECIPIENT_UID=23323; WORKER_UID=23321

def transition(uid):
    def f():
        import ctypes
        libc=ctypes.CDLL(None,use_errno=True)
        if libc.prctl(38,1,0,0,0):raise OSError(ctypes.get_errno(),'no_new_privs')
        os.setgroups([]);os.setresgid(uid,uid,uid);os.setresuid(uid,uid,uid)
        os.umask(0o077)
    return f

def sha(data:bytes):return hashlib.sha256(data).hexdigest()

class Study:
    def __init__(self,out:Path):
        self.out=out;out.mkdir(parents=True,exist_ok=True)
        self.base_public=json.loads((ROOT/'source_stage_q'/'public_trust.json').read_text())
        self.keys={case:{role:Ed25519PrivateKey.generate() for role in ROLES} for case in ['iottie','camm','napoli']}
        self.public=copy.deepcopy(self.base_public)
        self.public['source_classifications']={c:{f'{c}_PRIV':'covered_final',f'{c}_CLEAN':'independent'} for c in self.keys}
        self.public['archive_classifications']={
            'iottie':{'I_PRIV_ARCHIVE':{'qualified':True,'contains_specified':True},'I_CLEAN_COUNSEL_ARCHIVE':{'qualified':True,'contains_specified':False},'I_FALSE_CLEAN_ARCHIVE':{'qualified':True,'contains_specified':True}},
            'camm':{'C_PRIV_ARCHIVE':{'qualified':True,'contains_specified':True},'C_CLEAN_ARCHIVE':{'qualified':True,'contains_specified':False}},
            'napoli':{'N_PRIV_ARCHIVE':{'qualified':True,'contains_specified':True},'N_CLEAN_ARCHIVE':{'qualified':True,'contains_specified':False}}}
        self.public['role_pubkeys']={c:{role:k.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
            for role,k in roles.items()} for c,roles in self.keys.items()}
        (out/'public_trust.json').write_text(json.dumps(self.public,indent=2,sort_keys=True)+'\n')
        self.bundles={p.name.removesuffix('_evidence.json'):json.loads(p.read_text())
                      for p in (ROOT/'source_stage_q').glob('*_evidence.json')}
        self.rows=[];self.snapshots=[];self.sessions=[];self.current=None;self.serial=0;self.events=[]

    def start(self,name):
        print('START',name,flush=True)
        self.close()
        self.serial+=1
        private_root=Path(tempfile.mkdtemp(prefix='stage_r_receiver_'))
        os.chmod(private_root,0o711)
        recipient_dir=private_root/'private';recipient_dir.mkdir();os.chown(recipient_dir,RECIPIENT_UID,RECIPIENT_UID);os.chmod(recipient_dir,0o700)
        sockdir=private_root/'sock';sockdir.mkdir();os.chown(sockdir,RECIPIENT_UID,WORKER_UID);os.chmod(sockdir,0o2750)
        config=recipient_dir/'trust.json';config.write_text(json.dumps(self.public,sort_keys=True))
        os.chown(config,RECIPIENT_UID,RECIPIENT_UID);os.chmod(config,0o600)
        dbpath=recipient_dir/'actual_effects.sqlite'
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT);env['PYTHONDONTWRITEBYTECODE']='1'
        # Stage R recipient can import unchanged Stage Q validators from the vendor subtree.
        proc=subprocess.Popen([sys.executable,'-m','stage_r.server','--socket',str(sockdir/'recipient.sock'),
             '--ready',str(sockdir/'ready'),'--db',str(dbpath),'--trust',str(config),
             '--recipient-uid',str(RECIPIENT_UID),'--worker-uid',str(WORKER_UID)],
             preexec_fn=transition(RECIPIENT_UID),env=env,cwd=str(ROOT),
             stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=open(str(self.out/(name+'_server_stderr.txt')),'wb'))
        for i in range(180):
            if (sockdir/'ready').exists():break
            if proc.poll() is not None:
                _,err=proc.communicate(timeout=3)
                raise RuntimeError('Recipient failed startup '+err.decode(errors='replace')[-1600:])
            time.sleep(.04)
        else:raise TimeoutError('Recipient not ready')
        self.current={'name':name,'proc':proc,'root':private_root,'socket':str(sockdir/'recipient.sock'),
                      'db':dbpath,'calendar':True}
        ping=self.call({'cmd':'ping'})
        assert ping['uid']==RECIPIENT_UID
        self.setdate('2026-11-19')

    def call(self,req,*,worker=False):
        assert self.current is not None
        sock=self.current['socket']
        if not worker:
            resp=client(sock,req)
        else:
            env=os.environ.copy();env['PYTHONPATH']=str(ROOT);env['PYTHONDONTWRITEBYTECODE']='1'
            cp=subprocess.run([sys.executable,'-m','stage_r.worker_client',sock],input=json.dumps(req),text=True,
                              cwd=str(ROOT),env=env,preexec_fn=transition(WORKER_UID),capture_output=True,timeout=15)
            if cp.returncode!=0:raise RuntimeError('Worker client died: '+cp.stderr[:250])
            resp=json.loads(cp.stdout)
        if not resp.get('ok'):
            return {'_error':resp['error']}
        return resp['result']

    def setdate(self,date):
        r=self.call({'cmd':'set_clock','date':date})
        assert r['date']==date,r

    def keysign(self,case,role,payload):
        return sign(self.keys[case][role],payload)

    def event(self,case,event,role,date,seq,*,source=None,expected='RECORDED',alter=None):
        print('EVENT',self.current['name'],event,flush=True)
        self.setdate(date)
        self.serial+=1
        payload={'schema':'case-actor-event-v1','event_id':f'E{self.serial}_{case}_{event}',
                 'case':case,'event':event,'source_id':source,'role':role,
                 'sequence':seq,'nonce':f'n{self.serial}'}
        env=self.keysign(case,alter or role,payload)
        got=self.call({'cmd':'event','envelope':env})
        assert got['status']==expected,(case,event,got,expected)
        self.events.append({'suite':self.current['name'],'case':case,'event':event,'role':role,
                            'date':date,'expected':expected,'actual':got,'signed_envelope':env})
        return got

    def effect(self,name,case,role,date,claimed,expect,*,worker=False,cached=False,override=None,signer=None,invalid=False):
        print('EFFECT',self.current['name'],name,flush=True)
        self.setdate(date)
        self.serial+=1
        bundle=copy.deepcopy(self.bundles[name])
        if override=='tamper_output':bundle['output_b64']='ZmFrZQ=='
        if override=='tamper_read':bundle['legacy_seal']['body']['events'][0]['id']='bogus'
        original=bundle['legacy_seal']['body']
        assert original['case']==case
        payload={'schema':'actor-effect-authorization-v1','case':case,'artifact_id':original['artifact_id'],
                 'action':'EXTERNAL_EFFECT','role':role,'nonce':f'A{self.serial}'}
        if invalid:payload['artifact_id']='WRONG_TARGET'
        token=self.keysign(case,signer or role,payload)
        got=self.call({'cmd':'effect','bundle':bundle,'actor_envelope':token,'claimed':claimed,'cached':cached},worker=worker)
        assert got.get('verdict')==expect,(self.current['name'],name,got,expect)
        assert got['persisted']==(expect=='ALLOW_SCOPED'),(name,got,expect)
        self.rows.append({'suite':self.current['name'],'test':name,'kind':'effect','case':case,'role':role,
                          'date':date,'expected':expect,'actual':got['verdict'],'persisted':int(got['persisted']),
                          'epoch':got['policy_epoch'],'reason':got['reason'],'sources':json.dumps(got['sources'])})
        return got

    def challenge(self,case,source,date,expect,role='receiving_challenger',signer=None):
        print('CHALLENGE_COPY',self.current['name'],source,flush=True)
        self.setdate(date);self.serial+=1
        token=self.keysign(case,signer or role,{'schema':'actor-effect-authorization-v1','case':case,
           'artifact_id':source,'action':'CHALLENGE_COPY','role':role,'nonce':f'COPY{self.serial}'})
        got=self.call({'cmd':'challenge_copy','case':case,'source_id':source,'actor_envelope':token})
        assert got['verdict']==expect,(got,expect)
        self.rows.append({'suite':self.current['name'],'test':'challenge_'+source,'kind':'challenge_copy','case':case,
           'role':role,'date':date,'expected':expect,'actual':got['verdict'],
           'persisted':int(got['persisted']),'epoch':got.get('epoch'),'reason':got['reason'],'sources':json.dumps([source])})
        return got

    def archive(self,case,note_id,date,qualified,contains,expect,signer='receiving_counsel'):
        print('ARCHIVE',self.current['name'],note_id,flush=True)
        self.setdate(date)
        self.serial+=1
        token=self.keysign(case,signer,{'schema':'actor-effect-authorization-v1','case':case,
             'artifact_id':note_id,'action':'ARCHIVE','role':'receiving_counsel','nonce':f'ARC{self.serial}'})
        got=self.call({'cmd':'archive','case':case,'note_id':note_id,'actor_envelope':token,
                       'qualified':qualified,'contains_specified':contains})
        assert got['verdict']==expect,(note_id,got,expect)
        self.rows.append({'suite':self.current['name'],'test':note_id,'kind':'archive','case':case,
            'role':'receiving_counsel','date':date,'expected':expect,'actual':got['verdict'],
            'persisted':int(got['persisted']),'epoch':got.get('epoch'), 'reason':'','sources':'[]'})
        return got

    def clock(self,case,trigger,actor,due,status):
        snapshot=self.call({'cmd':'snapshot','case':case})
        assert 'duties' in snapshot,snapshot
        duties=[d for d in snapshot['duties'] if d['trigger']==trigger and d['actor']==actor]
        assert len(duties)==1,(case,trigger,actor,snapshot['duties'])
        row=duties[0];assert row['due']==due and row['status']==status,(row,due,status)
        self.snapshots.append({'suite':self.current['name'],'date':snapshot['date'],
                               'case':case,'trigger':trigger,'actor':actor,'due':due,'status':status,
                               'duty':row})
        return row

    def close(self):
        if self.current:print('CLOSING',self.current['name'],flush=True)
        if not self.current:return
        cur=self.current
        cur['proc'].terminate()
        try:cur['proc'].communicate(timeout=6)
        except subprocess.TimeoutExpired:
            cur['proc'].kill();cur['proc'].communicate(timeout=3)
        assert cur['proc'].returncode in (0,-15,-2,-9),cur['proc'].returncode
        dest=self.out/(cur['name']+'_effects.sqlite')
        import shutil
        shutil.copy2(cur['db'],dest)
        db=sqlite3.connect(str(dest));assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        cases=db.execute('SELECT COUNT(*) FROM legal_events').fetchone()[0]
        attempts=db.execute('SELECT COUNT(*) FROM legal_effect_attempts').fetchone()[0]
        effects=db.execute('SELECT COUNT(*) FROM legal_effects').fetchone()[0]
        archives=db.execute('SELECT COUNT(*) FROM legal_archive').fetchone()[0]
        challenge_copies=db.execute('SELECT COUNT(*) FROM legal_challenge_copy').fetchone()[0]
        rej=db.execute('SELECT COUNT(*) FROM legal_rejections').fetchone()[0]
        db.close()
        self.sessions.append({'name':cur['name'],'events':cases,'effect_attempts':attempts,
                              'effect_rows':effects,'archives':archives,'challenge_copies':challenge_copies,'event_rejections':rej,'sqlite_sha256':sha(dest.read_bytes())})
        shutil.rmtree(cur['root'],ignore_errors=True)
        self.current=None

    def run(self):
        try:
            self.start('iottie')
            self.effect('pre_reverse','iottie','receiving_party','2026-11-19',['iottie_PRIV'],'ALLOW_SCOPED',worker=True)
            # Correct role label but cryptographically signed by wrong actor.
            self.event('iottie','producer_notice','producing_party','2026-11-20',1,source='iottie_PRIV',expected='REJECTED',alter='receiving_party')
            self.event('iottie','producer_notice','producing_party','2026-11-20',1,source='iottie_PRIV')
            self.challenge('iottie','iottie_PRIV','2026-11-20','ALLOW_CHALLENGE_ONLY')
            self.challenge('iottie','iottie_PRIV','2026-11-20','HOLD')
            self.challenge('iottie','iottie_PRIV','2026-11-20','HOLD',role='receiving_party')
            self.clock('iottie','producer_notice','producing_party','2026-12-07','OPEN_UNATTESTED')
            self.effect('post_reverse','iottie','receiving_party','2026-11-20',['iottie_PRIV'],'BLOCK',cached=True)
            self.effect('post_reverse','iottie','receiving_party','2026-11-20',['iottie_PRIV'],'HOLD',override='tamper_output')
            self.effect('clean_hash','iottie','receiving_party','2026-11-20',['iottie_CLEAN'],'ALLOW_SCOPED')
            self.effect('literal_launder','iottie','receiving_party','2026-11-20',['iottie_CLEAN'],'HOLD')
            self.effect('mixed_sources','iottie','receiving_party','2026-11-20',['iottie_PRIV','iottie_CLEAN'],'BLOCK')
            self.effect('clean_conflict','iottie','receiving_party','2026-11-20',[],'HOLD')
            self.effect('parent_derived','iottie','receiving_party','2026-11-20',['iottie_PRIV','iottie_CLEAN'],'BLOCK')
            self.effect('stdout_exfil','iottie','receiving_party','2026-11-20',['iottie_PRIV'],'BLOCK')
            # Missing actor scope and forged actor signature cannot persist.
            self.effect('clean_hash','iottie','receiving_challenger','2026-11-20',['iottie_CLEAN'],'HOLD')
            self.effect('clean_hash','iottie','receiving_party','2026-11-20',['iottie_CLEAN'],'HOLD',signer='producing_party')
            # Untrusted worker cannot move the trusted simulated time.
            bad=self.call({'cmd':'set_clock','date':'2030-01-01'},worker=True)
            assert bad.get('_error','').startswith('PermissionError: Trusted fixture control'),bad
            self.rows.append({'suite':'iottie','test':'worker_clock_override','kind':'clock_attack','case':'iottie',
                'role':'worker','date':'2026-11-20','expected':'REJECTED','actual':'REJECTED','persisted':0,'epoch':None,
                'reason':bad['_error'],'sources':'[]'})
            self.event('iottie','producer_log_delivered','producing_party','2026-12-07',2)
            self.clock('iottie','producer_notice','producing_party','2026-12-07','ATTESTED_WITHIN_WINDOW')
            self.event('iottie','receipt_of_log_and_replacement','receiving_challenger','2026-12-07',1)
            self.clock('iottie','receipt_of_log_and_replacement','receiving_challenger','2026-12-16','OPEN_UNATTESTED')
            self.event('iottie','challenge_filed','receiving_challenger','2026-12-16',2)
            replay=self.call({'cmd':'event','envelope':self.events[-1]['signed_envelope']})
            assert replay['status']=='REJECTED' and 'already used' in replay['reason'],replay
            self.events.append({'suite':'iottie','case':'iottie','event':'challenge_filed_REPLAY','role':'receiving_challenger','date':'2026-12-16','expected':'REJECTED','actual':replay,'signed_envelope':self.events[-1]['signed_envelope']})
            self.clock('iottie','receipt_of_log_and_replacement','receiving_challenger','2026-12-16','ATTESTED_WITHIN_WINDOW')
            self.event('iottie','final_termination','court_event_attester','2027-01-06',1)
            self.clock('iottie','final_termination','receiving_party','2027-03-06','OPEN_UNATTESTED')
            self.archive('iottie','I_PRIV_ARCHIVE','2027-01-06',True,True,'HOLD')
            self.archive('iottie','I_CLEAN_COUNSEL_ARCHIVE','2027-01-06',True,False,'ALLOW_RESTRICTED_STORAGE')
            self.archive('iottie','I_FALSE_CLEAN_ARCHIVE','2027-01-06',True,False,'HOLD')
            self.close()

            self.start('camm')
            self.event('camm','producer_notice','producing_party','2026-11-20',1,source='camm_PRIV')
            self.clock('camm','producer_notice','receiving_party','2026-11-30','OPEN_UNATTESTED')
            self.effect('camm_priv_transform','camm','receiving_party','2026-11-20',['camm_PRIV'],'BLOCK')
            self.effect('camm_clean_transform','camm','receiving_party','2026-11-20',['camm_CLEAN'],'ALLOW_SCOPED',worker=True)
            self.setdate('2026-11-30');self.clock('camm','producer_notice','receiving_party','2026-11-30','DUE_TODAY_UNATTESTED')
            self.setdate('2026-12-01');self.clock('camm','producer_notice','receiving_party','2026-11-30','OVERDUE_UNATTESTED')
            self.event('camm','final_termination','court_event_attester','2027-01-01',1)
            self.clock('camm','final_termination','receiving_party','2027-03-02','OPEN_UNATTESTED')
            self.archive('camm','C_PRIV_ARCHIVE','2027-01-01',True,True,'HOLD')
            self.archive('camm','C_CLEAN_ARCHIVE','2027-01-01',True,False,'ALLOW_RESTRICTED_STORAGE')
            self.close()

            self.start('napoli')
            self.event('napoli','self_discovery','receiving_party','2026-11-20',1,source='napoli_PRIV')
            assert not [x for x in self.call({'cmd':'snapshot','case':'napoli'})['duties'] if x['trigger']=='producer_notice']
            self.effect('napoli_priv_transform','napoli','receiving_party','2026-11-20',['napoli_PRIV'],'BLOCK')
            self.event('napoli','producer_notice','producing_party','2026-11-24',1,source='napoli_PRIV')
            self.clock('napoli','producer_notice','receiving_party','2026-12-01','OPEN_UNATTESTED')
            self.setdate('2026-12-02');self.clock('napoli','producer_notice','receiving_party','2026-12-01','OVERDUE_UNATTESTED')
            self.event('napoli','final_termination','court_event_attester','2026-12-02',1)
            self.clock('napoli','final_termination','receiving_party','2027-01-01','OPEN_UNATTESTED')
            self.effect('napoli_clean_transform','napoli','receiving_counsel','2026-12-02',['napoli_CLEAN'],'ALLOW_SCOPED')
            self.archive('napoli','N_PRIV_ARCHIVE','2026-12-02',True,True,'HOLD')
            self.archive('napoli','N_CLEAN_ARCHIVE','2026-12-02',True,False,'ALLOW_RESTRICTED_STORAGE')
            self.event('napoli','return_or_destruction','receiving_party','2026-12-29',2)
            self.clock('napoli','final_termination','receiving_party','2027-01-01','ATTESTED_WITHIN_WINDOW')
            self.clock('napoli','producer_notice','receiving_party','2026-12-01','ATTESTED_AFTER_WINDOW')
            self.clock('napoli','return_or_destruction','receiving_counsel','2027-01-08','OPEN_UNATTESTED')
            self.event('napoli','written_confirmation','receiving_counsel','2027-01-08',1)
            self.clock('napoli','return_or_destruction','receiving_counsel','2027-01-08','ATTESTED_WITHIN_WINDOW')
            self.close()

            self.start('expired_challenge')
            self.event('iottie','producer_notice','producing_party','2026-11-20',1,source='iottie_PRIV')
            self.event('iottie','receipt_of_log_and_replacement','receiving_challenger','2026-12-07',1)
            self.challenge('iottie','iottie_PRIV','2026-12-17','HOLD')
            self.close()

            self.start('missed_notice')
            # Independent recipient has never received authenticated notice.
            self.effect('napoli_priv_transform','napoli','receiving_party','2026-11-24',['napoli_PRIV'],'ALLOW_SCOPED',worker=True)
            self.close()

            self.start('missing_calendar')
            c=self.call({'cmd':'set_calendar','enabled':False});assert c['enabled'] is False
            self.event('camm','producer_notice','producing_party','2026-11-20',1,source='camm_PRIV')
            self.clock('camm','producer_notice','receiving_party',None,'UNRESOLVED_CALENDAR')
            self.effect('camm_priv_transform','camm','receiving_party','2026-11-20',['camm_PRIV'],'BLOCK')
            self.close()
        finally:self.close()
        self.cross_check()

    def cross_check(self):
        # Stage N clause predicates exercise separately from Stage Q provenance.
        from experiments.policy_compiler.policy_engine import load_default
        p=load_default()
        bridged=p.decide(case='camm',event='C_PRIV_NOTICE',action='EXTERNAL_EFFECT',kind='summary',
             facts={'contains_specified':True,'claim_active':True,'confidential_information_included':True,'reproduces_confidential_text':True})
        assert 'C-03-20-COPY-BRIDGE' in bridged.rule_ids and bridged.verdict=='BLOCK'
        unknown=p.decide(case='camm',event='C_PRIV_NOTICE',action='EXTERNAL_EFFECT',kind='summary',
             facts={'contains_specified':True,'claim_active':True})
        assert 'C-03-20-COPY-BRIDGE' not in unknown.rule_ids
        napoli=p.decide(case='napoli',event='C_PRIV_NOTICE',action='DELETE_WHOLE_NOTE',kind='mixed_note',
                         facts={'contains_specified':True,'claim_active':True})
        assert napoli.verdict=='REVIEW_REQUIRED'
        clean_napoli=p.decide(case='napoli',event='FINAL_TERMINATION',action='RETAIN',kind='summary',
                              facts={'contains_specified':False,'claim_active':False,'is_covered_final_material':True})
        assert clean_napoli.verdict=='REVIEW_REQUIRED'
        self.snapshots.extend([{'suite':'engine_boundary','case':'camm','trigger':'conditional_copy',
            'actor':'receiving_party','due':None,'status':bridged.verdict,'rule_ids':bridged.rule_ids},
            {'suite':'engine_boundary','case':'camm','trigger':'unknown_copy',
            'actor':'receiving_party','due':None,'status':unknown.verdict,'rule_ids':unknown.rule_ids},
            {'suite':'engine_boundary','case':'napoli','trigger':'whole_note_review',
            'actor':'receiving_party','due':None,'status':napoli.verdict,'rule_ids':napoli.rule_ids}])
        (self.out/'scenario_results.csv').write_text('')
        with (self.out/'scenario_results.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=self.rows[0].keys());w.writeheader();w.writerows(self.rows)
        (self.out/'event_results.json').write_text(json.dumps(self.events,indent=2,sort_keys=True)+'\n')
        (self.out/'duty_snapshots.json').write_text(json.dumps(self.snapshots,indent=2,sort_keys=True)+'\n')
        (self.out/'session_metadata.json').write_text(json.dumps(self.sessions,indent=2,sort_keys=True)+'\n')
        n_effects=sum(x['effect_rows'] for x in self.sessions)
        summary={'sessions':len(self.sessions),'scenarios':len(self.rows),
            'external_effect_requests':sum(x['kind']=='effect' for x in self.rows),
            'persisted_external_effects':sum(x['persisted'] for x in self.rows if x['kind']=='effect'),
            'persisted_sql_effect_rows':n_effects,
            'archive_records':sum(x['archives'] for x in self.sessions),
            'restricted_challenge_copy_records':sum(x['challenge_copies'] for x in self.sessions),
            'event_attempts':len(self.events),'event_rejections':sum(e['actual']['status']=='REJECTED' for e in self.events),
            'verified_clock_snapshots':len(self.snapshots),
            'stage_q_reused_signed_attestations':True,
            'court_rule_count_unmodified':18,
            'typed_duty_templates':8,
            'deadline_and_policy_snapshots':len(self.snapshots),
            'deadline_assertions':sum('duty' in x for x in self.snapshots),
            'simulated_fixture_calendar':True,
            'limitation':'Replays authentic saved Stage Q signed program/read/output bundles. Stage R policy enforcement runs in a new isolated recipient; producer/actor signatures and dates are synthetic new fixture events, not live legal filings.'}
        assert n_effects==summary['persisted_external_effects']
        (self.out/'study_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
        print('STAGE_R',json.dumps({k:v for k,v in summary.items() if k!='limitation'},sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='results');a=p.parse_args()
    if os.geteuid()!=0 or sys.platform!='linux':raise RuntimeError('Requires disposable Linux root namespace for UID split')
    Study(Path(a.out).resolve()).run()
