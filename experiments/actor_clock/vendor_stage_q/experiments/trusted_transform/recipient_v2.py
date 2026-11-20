"""Recipient that requires BOTH broker-observed reads and code/byte binding.

Attestation validation occurs before the legacy recipient's atomic policy + write
transaction. V1-only submissions are not accepted by this service.
"""
from __future__ import annotations
import argparse,base64,json,os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from experiments.enforced_custody.ipc import serve
from experiments.policy_compiler.verified_recipient import VerifiedRecipient,EvidenceError,verify,digest
from experiments.policy_compiler.policy_engine import stable_json

V2_FIELDS={'schema','run_id','artifact_id','case','kind','program_sha256','launcher_sha256',
           'output_sha256','observed_event_count','events_sha256','legacy_seal_sha256',
           'worker_uid','broker_uid','sandbox_profile'}

def validate_v2(gate,legacy,att,output,expected_launcher,broker_uid,worker_uid):
    body=verify(gate.broker_pub,att,V2_FIELDS)
    legacy_body=verify(gate.broker_pub,legacy,gate.SEAL_FIELDS)
    if body['schema']!='broker-run-code-binding-v1' or legacy_body['schema']!='broker-observed-reads-v1':
        raise EvidenceError('Unexpected proof schemas')
    if body['sandbox_profile']!='uid-dac-no-new-privs-seccomp-deny-v1':
        raise EvidenceError('Unknown sandbox profile')
    if type(body['worker_uid']) is not int or type(body['broker_uid']) is not int:
        raise EvidenceError('UIDs not integral')
    if body['broker_uid']!=broker_uid or body['worker_uid']!=worker_uid or broker_uid==worker_uid:
        raise EvidenceError('Execution identity mismatch')
    if body['launcher_sha256']!=expected_launcher:raise EvidenceError('Unexpected trusted launcher')
    if not isinstance(body['program_sha256'],str) or len(body['program_sha256'])!=64:
        raise EvidenceError('Missing program identity')
    for k in ('run_id','artifact_id','case','kind','output_sha256'):
        if body[k]!=legacy_body[k]:raise EvidenceError('Cross-attestation mismatch: '+k)
    if body['output_sha256']!=digest(output):raise EvidenceError('Actual output bytes changed')
    if body['legacy_seal_sha256']!=digest(stable_json(legacy).encode()):
        raise EvidenceError('Legacy seal replaced')
    events=legacy_body['events']
    if body['events_sha256']!=digest(stable_json(events).encode()) or body['observed_event_count']!=len(events):
        raise EvidenceError('Read-set mismatch')
    if not legacy_body['closed'] or not events:raise EvidenceError('Incomplete read closure')
    return body

def run(a):
    if os.geteuid()!=a.recipient_uid or a.recipient_uid in (0,a.worker_uid,a.broker_uid):
        raise PermissionError('Recipient UID mismatch')
    pub=serialization.load_pem_public_key(Path(a.broker_pubkey).read_bytes())
    cfg=json.loads(Path(a.config).read_text())
    owners={k:serialization.load_pem_public_key(v.encode()) for k,v in cfg['owner_pub'].items()}
    gate=VerifiedRecipient(Path(a.db),pub,owners)
    gate.db.execute('''CREATE TABLE IF NOT EXISTS execution_rejections (
        rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id TEXT, proof_sha256 TEXT NOT NULL, reason TEXT NOT NULL, policy_epoch INTEGER NOT NULL
    )''')
    for case,sid,sha in cfg['pinned_sources']:
        gate.db.execute('INSERT OR IGNORE INTO sources(case_id,source_id,source_sha256) VALUES(?,?,?)',(case,sid,sha))
    def handler(msg,uid):
        cmd=msg.get('cmd')
        if cmd=='notice':
            if set(msg)!={'cmd','envelope'}:raise EvidenceError('Malformed notice route')
            return {'epoch':gate.accept_owner_notice(msg['envelope'])}
        if cmd=='attempt':
            if set(msg)!={'cmd','bundle','claimed_sources','cached_approval'}:raise EvidenceError('Malformed attempt route')
            bundle=msg['bundle']
            if not isinstance(bundle,dict) or set(bundle)!={'schema','output_b64','legacy_seal','execution_attestation'}:
                raise EvidenceError('Program-attested bundle required')
            if bundle['schema']!='trusted-transform-bundle-v1':raise EvidenceError('Unknown bundle')
            output=base64.b64decode(bundle['output_b64'],validate=True)
            if len(output)>65536:raise EvidenceError('Output too long')
            try:
                code=validate_v2(gate,bundle['legacy_seal'],bundle['execution_attestation'],output,
                                 cfg['launcher_sha256'],a.broker_uid,a.worker_uid)
                if code['program_sha256'] not in cfg['approved_program_sha256']:
                    raise EvidenceError('Program digest not in recipient-approved registry')
            except (ValueError,KeyError,TypeError) as e:
                # Invalid proof is durably audited under an atomic read of current epoch.
                # Crucially, legacy effect writer is NEVER invoked.
                reason='Execution evidence invalid: '+str(e)[:220]
                from hashlib import sha256
                proof_sha=sha256(stable_json(bundle).encode()).hexdigest()
                gate.db.execute('BEGIN IMMEDIATE')
                try:
                    epoch=gate.db.execute('SELECT epoch FROM policy_epoch').fetchone()[0]
                    gate.db.execute('INSERT INTO execution_rejections(artifact_id,proof_sha256,reason,policy_epoch) VALUES(?,?,?,?)',
                                    (str(bundle.get('legacy_seal',{}).get('body',{}).get('artifact_id','UNKNOWN'))[:160],
                                     proof_sha,reason,epoch))
                    gate.db.execute('COMMIT')
                except BaseException:
                    gate.db.execute('ROLLBACK')
                    raise
                return {'status':'HOLD','persisted':False,'reason':reason,
                        'evidence_status':('UNAPPROVED_PROGRAM' if 'not in recipient-approved' in reason else 'INVALID_EXECUTION_PROOF'),
                        'epoch':epoch,
                        'resolved_sources':[],'program_sha256':None}
            d=gate.attempt_effect(bundle['legacy_seal'],output,msg['claimed_sources'],cached_approval=msg['cached_approval'])
            return {'status':d.status,'persisted':d.persisted,'reason':d.reason,
                    'evidence_status':d.evidence_status,'epoch':d.policy_epoch,
                    'resolved_sources':list(d.resolved_sources),'program_sha256':code['program_sha256']}
        raise EvidenceError('Unsupported recipient command')
    try:serve(a.socket,{a.worker_uid,0},handler,a.ready)
    finally:gate.close()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for s in ('socket','broker-pubkey','config','db','ready'):p.add_argument('--'+s,required=True)
    for s in ('worker-uid','broker-uid','recipient-uid'):p.add_argument('--'+s,required=True,type=int)
    run(p.parse_args())
