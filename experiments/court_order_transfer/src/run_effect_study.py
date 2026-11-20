#!/usr/bin/env python3
"""Re-run immutable scenario matrix against distinct recipient processes."""
from __future__ import annotations
from pathlib import Path
import json,csv,os,hashlib,secrets,subprocess,sys,time,urllib.request,sqlite3,socket
R=Path(__file__).resolve().parents[1]

def post(port,path,obj):
    req=urllib.request.Request('http://127.0.0.1:%d%s'%(port,path),data=json.dumps(obj).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def run(mode,root):
    root.mkdir(parents=True,exist_ok=True)
    items=list(csv.DictReader((R/'gold/scenario_oracle.csv').open()))
    # The receiver itself sees no scenario expected labels. Runner only passes request-side fields.
    keys={'token_secret':secrets.token_hex(32),'owner_auth':secrets.token_hex(24)}
    keyfile=root/'keys_private_test_only.json';keyfile.write_text(json.dumps(keys));os.chmod(keyfile,0o600)
    port=free_port();db=root/'recipient.sqlite'
    cmd=[sys.executable,str(R/'src/effect_receiver.py'),'--db',str(db),'--port',str(port),'--keyfile',str(keyfile),'--proposals',str(R/'results/one_shot_policy_proposals.json')]
    with (root/'server.log').open('w') as f:
      proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT)
    try:
      for _ in range(100):
        try:
          with urllib.request.urlopen(f'http://127.0.0.1:{port}/ping',timeout=.2) as a:
             if json.load(a)['alive']:break
        except:time.sleep(.04)
      else:raise RuntimeError('server did not start')
      details=[]
      for i,s in enumerate(items):
        case=s['case_id'];scenario=s['scenario_id'];kind=s['source_kind'];effect=s['requested_effect'];actor=s['actor']
        content=('SYNTHETIC_PROTECTED_EXCERPT_' if kind=='protected' else 'SYNTHETIC_INDEPENDENT_CLEAN_')+scenario
        body={'permit_id':f'{mode}-{scenario}-preissued','case_id':case,'scenario_id':scenario,'source_kind':kind,'actor':actor,'effect':effect,'content_sha256':hashlib.sha256(content.encode()).hexdigest()}
        # issue before any revocation events, as required by the scenario
        permit=post(port,'/issue',{'owner_auth':keys['owner_auth'],'token_body':body})
        # Notice only delivered when scenario says received; receiver never sees the gold event otherwise.
        if s['receiver_notice']=='recipient_informed' and s['real_event']!='pre_notice':
             assert post(port,'/notice',{'owner_auth':keys['owner_auth'],'case_id':case,'scenario_id':scenario,'event':s['real_event']})['received']
        result=post(port,'/write',{'owner_auth':keys['owner_auth'],'permit':permit,'scenario_id':scenario,'case_id':case,'source_kind':kind,'actor':actor,'effect':effect,'mode':mode,'content':content})
        details.append({'scenario_id':scenario,'observed':result,'expected':s['expected']})
      (root/'runner_responses.json').write_text(json.dumps(details,indent=2)+'\n')
      return {'mode':mode,'attempts':len(items),'persisted':sum(x['observed']['persisted'] for x in details)}
    finally:
      proc.terminate()
      try:proc.wait(timeout=5)
      except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();base=Path(a.output)
 print(json.dumps([run('static',base/'static'),run('gated',base/'gated')],indent=2))
