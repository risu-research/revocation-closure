"""Broker-owned reading and sealed execution attestations for an untrusted script.

The plugin is a separate worker UID; it cannot open the vault or use broker keys.
The broker measures a root-owned program before delivery to the worker. It signs
observed source/parent reads plus ACTUAL returned output bytes, not client labels.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, socket, stat
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from experiments.policy_compiler.verified_recipient import TrustedReadBroker,digest,sign
from experiments.policy_compiler.policy_engine import stable_json

MAX=1_200_000

def send(sock,obj):
    raw=json.dumps(obj,sort_keys=True,separators=(',',':')).encode()+b'\n'
    if len(raw)>MAX:raise ValueError('Oversized reply')
    sock.sendall(raw)

_SOCKET_READER=None

def receive(sock):
    global _SOCKET_READER
    if _SOCKET_READER is None:
        _SOCKET_READER=sock.makefile('rb')
    data=_SOCKET_READER.readline(MAX+1)
    if not data or len(data)>MAX or not data.endswith(b'\n'):
        raise ValueError('Malformed or closed worker stream')
    return json.loads(data)

def safe_program(path):
    p=Path(path);st=os.lstat(p)
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_mode&0o022:
        raise PermissionError('Program must be immutable root-owned regular file')
    # Parent directory must also be protected against worker rewrites.
    dr=os.stat(p.parent)
    if dr.st_uid!=0 or dr.st_mode&0o022:raise PermissionError('Program directory mutable')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:data=os.read(fd,32769)
    finally:os.close(fd)
    if not data or len(data)>32768:raise ValueError('Program size invalid')
    return data

def run(a):
    if os.geteuid()!=a.broker_uid or a.broker_uid in (0,a.worker_uid):raise PermissionError('Broker UID invalid')
    sock=socket.socket(fileno=a.fd)
    vault_fd=os.open(a.vault,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    idxfd=os.open('index.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=vault_fd)
    with os.fdopen(idxfd) as f:registry=json.load(f)
    kfd=os.open('broker_private.pem',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=vault_fd)
    with os.fdopen(kfd,'rb') as f: private=serialization.load_pem_private_key(f.read(),password=None)
    if not isinstance(private,Ed25519PrivateKey):raise ValueError('Invalid broker signing key')
    code=safe_program(a.program)
    launcher=safe_program(a.launcher)
    code_hash=digest(code); launcher_hash=digest(launcher)
    broker=TrustedReadBroker(private)
    broker.open_run(a.run_id,a.artifact_id,a.case,a.kind)
    send(sock,{'cmd':'init','program_b64':base64.b64encode(code).decode(),
               'program_sha256':code_hash,'run_id':a.run_id})
    ready=receive(sock)
    if ready!={'cmd':'ready','seccomp_loaded':True}:raise ValueError('Worker failed readiness')
    observations=0
    for _ in range(40):
        req=receive(sock)
        if not isinstance(req,dict) or not isinstance(req.get('cmd'),str):raise ValueError('Bad worker request')
        if req['cmd']=='read':
            if set(req)!={'cmd','source_id'}:raise ValueError('Extra read fields')
            sid=req['source_id']; info=registry.get(sid)
            if not isinstance(sid,str) or not info or info['case']!=a.case:raise PermissionError('Unpinned or cross-case read')
            filename=info['filename']
            if not isinstance(filename,str) or filename in ('','.','..') or '/' in filename or '\\' in filename:
                raise ValueError('Invalid source filename')
            fd=os.open(filename,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=vault_fd)
            try:raw=os.read(fd,65537)
            finally:os.close(fd)
            if len(raw)>65536 or digest(raw)!=info['sha256']:raise ValueError('Pinned content modified')
            broker.observe_source(a.run_id,sid,raw);observations+=1
            send(sock,{'ok':True,'result':{'bytes_b64':base64.b64encode(raw).decode(),'sha256':digest(raw)}})
        elif req['cmd']=='parent':
            if set(req)!={'cmd','artifact_id'} or not isinstance(req['artifact_id'],str):raise ValueError('Invalid parent')
            broker.observe_parent(a.run_id,req['artifact_id']);observations+=1
            send(sock,{'ok':True,'result':{'artifact_id':req['artifact_id']}})
        elif req['cmd']=='complete':
            if set(req)!={'cmd','output_b64'}:raise ValueError('Unexpected completion fields')
            if observations==0:raise ValueError('No observed read/parent; cannot assert closed dependencies')
            out=base64.b64decode(req['output_b64'],validate=True)
            if len(out)>65536:raise ValueError('Output over size bound')
            oldseal=broker.seal(a.run_id,out)
            old_body=oldseal['body']
            # Program bytes and read log/returned bytes are all measured by broker.
            att=sign(private,{'schema':'broker-run-code-binding-v1','run_id':a.run_id,
                              'artifact_id':a.artifact_id,'case':a.case,'kind':a.kind,
                              'program_sha256':code_hash,'launcher_sha256':launcher_hash,
                              'output_sha256':digest(out),
                              'observed_event_count':len(old_body['events']),
                              'events_sha256':digest(stable_json(old_body['events']).encode()),
                              'legacy_seal_sha256':digest(stable_json(oldseal).encode()),
                              'worker_uid':a.worker_uid,'broker_uid':a.broker_uid,
                              'sandbox_profile':'uid-dac-no-new-privs-seccomp-deny-v1'})
            output={'schema':'trusted-transform-bundle-v1',
                    'output_b64':base64.b64encode(out).decode(),
                    'legacy_seal':oldseal,'execution_attestation':att}
            Path(a.result).write_text(stable_json(output)+'\n')
            send(sock,{'ok':True,'result':'SEALED'})
            return
        elif req['cmd']=='fail':
            raise RuntimeError('Plugin failed: '+str(req.get('error_type','unknown')))
        else: raise ValueError('Unsupported plugin command')
    raise ValueError('Too many reads')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('vault','program','launcher','case','kind','run-id','artifact-id','result'):p.add_argument('--'+name,required=True)
    for name in ('fd','worker-uid','broker-uid'):p.add_argument('--'+name,required=True,type=int)
    run(p.parse_args())
