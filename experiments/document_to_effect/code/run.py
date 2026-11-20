"""Replay a documented source read, signed write permit and recipient decision."""
from __future__ import annotations
import argparse,base64,csv,json,os,socket,sqlite3,subprocess,sys,tempfile,time,uuid,copy
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from common import keypair,signed,sha,canon,post,get
from agent import produce

ROOT=Path(__file__).resolve().parents[1]

def freeport():
 s=socket.socket();s.bind(('127.0.0.1',0));v=s.getsockname()[1];s.close();return v

def start(script,args,log):
 h=open(log,'wb');p=subprocess.Popen([sys.executable,str(ROOT/'code'/script),*args],stdout=h,stderr=subprocess.STDOUT,cwd=str(ROOT/'code'),env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});return p,h

def until(url,proc):
 for i in range(160):
  if proc.poll()!=None:raise RuntimeError('service exit '+str(proc.returncode))
  try:
   if get(url+'/ping')['ok']:return
  except Exception:time.sleep(.06)
 raise RuntimeError('service did not start')

class Study:
 def __init__(self,out):
  self.out=out;out.mkdir(parents=True,exist_ok=True)
  self.src_key,self.source_pub=keypair();self.issuer,self.issuer_pub=keypair();self.producer,self.producer_pub=keypair();self.owner,self.owner_pub=keypair();self.receiver_actor,self.receiver_actor_pub=keypair()
  trust={'source_pub':self.source_pub,'issuer_pub':self.issuer_pub,'producer_pub':self.producer_pub,'owner_pub':self.owner_pub,'receiving_pub':self.receiver_actor_pub,'source_schema':'actual-tool-read-v1'}
  (out/'trust.json').write_text(json.dumps(trust,indent=2,sort_keys=True)+'\n')
  (out/'source_key.hex').write_text(self.src_key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()).hex())
  os.chmod(out/'source_key.hex',0o600)
  self.source_port=freeport();self.source_url=f'http://127.0.0.1:{self.source_port}'
  self.sp,self.sh=start('source_server.py',['--port',str(self.source_port),'--db',str(out/'source_reads.sqlite'),'--key',str(out/'source_key.hex'),'--input',str(ROOT/'inputs'/'source_snapshot.json')],out/'source_server.log')
  until(self.source_url,self.sp);self.receivers=[];self.rows=[];self.events=[];self.artifacts=[];self.tool_calls=[];self.permits=[];self.request_archive=[];self.timeline=[];self.sequence=0
  (out/'source_snapshot_sha256.txt').write_text(sha((ROOT/'inputs'/'source_snapshot.json').read_bytes())+'\n')
 def receiver(self,name):
  port=freeport();url=f'http://127.0.0.1:{port}'
  proc,h=start('recipient_server.py',['--port',str(port),'--db',str(self.out/(name+'.sqlite')),'--trust',str(self.out/'trust.json')],self.out/(name+'_server.log'))
  until(url,proc);self.receivers.append((proc,h));return url
 def restart_receiver(self,name):
  # Real process restart over the same recipient-owned on-disk SQLite database.
  proc,h=self.receivers[-1];proc.terminate();proc.wait(timeout=5);h.close()
  port=freeport();url=f'http://127.0.0.1:{port}'
  p2,h2=start('recipient_server.py',['--port',str(port),'--db',str(self.out/(name+'.sqlite')),'--trust',str(self.out/'trust.json')],self.out/(name+'_restart_server.log'))
  until(url,p2);self.receivers.append((p2,h2));return url
 def memo(self,case,category,name):
  rid=f'{case}-{name}'
  choice={'priv':['PRIV'],'clean':['CLEAN'],'mixed':['PRIV','CLEAN']}[category]
  data,receipts,trace=produce(case,rid,self.source_url,choice)
  self.tool_calls.extend([{**x,'run_id':rid,'case':case} for x in trace]);self.artifacts.append({'run_id':rid,'case':case,'category':category,'output':data['content'],'output_hash':sha(data['content'])})
  return data,receipts
 def permit(self,data,receipts,name,*,expiry=5,target='legal-effects'):
  body={'schema':'preissued-execution-permit-v1','permit_id':f'{data["run_id"]}-{name}','case':data['case'],'audience':'INDEPENDENT_RECIPIENT','action':'STORE_DOCUMENT','target':target,'artifact_sha256':sha(data['content']),'source_ids':sorted(set(r['body']['source_id'] for r in receipts)),'issued_epoch':0,'expiry_epoch':expiry}
  env=signed(self.issuer,body);self.sequence+=1;self.permits.append({'sequence':self.sequence,'permit':env});self.timeline.append({'sequence':self.sequence,'kind':'ISSUE_PERMIT','case':data['case'],'permit_id':body['permit_id']});return env
 def write(self,case,name,url,mode,doc,receipts,permit,expected,*,owner=True,true_unsafe=None,oracle_notice_received=None):
  env=signed(self.owner,{'action':'STORE_DOCUMENT','permit_id':permit['body']['permit_id']}) if owner else None
  request={'mode':mode,'artifact':doc,'read_receipts':receipts,'permit':permit,'owner_envelope':env}
  self.sequence+=1;sequence=self.sequence
  output=post(url+'/write',request)
  self.request_archive.append({'case':case,'scenario':name,'recipient_db':self.current_db,'sequence':sequence,'request':request,'response':output});self.timeline.append({'sequence':sequence,'kind':'WRITE','case':case,'scenario':name,'permit_id':permit['body']['permit_id'],'recipient_db':self.current_db})
  actual=output['decision'];assert actual==expected,(case,name,mode,actual,expected,output)
  outcome={'case':case,'scenario':name,'mode':mode,'run_id':doc['run_id'],'permit_id':permit['body']['permit_id'],'expected':expected,'actual':actual,'persisted':bool(output['persisted']),'source_ids':permit['body']['source_ids'],'artifact_sha256':sha(doc['content']),'true_unsafe':bool(true_unsafe) if true_unsafe is not None else bool(output['persisted'] and 'PRIV' in str(permit['body']['source_ids']) and oracle_notice_received is not False),'recipient_acknowledged':bool(oracle_notice_received) if oracle_notice_received is not None else None,'recipient_db':self.current_db}
  self.rows.append(outcome);return output
 def notice(self,case,url,*,invalid=False):
  body={'schema':'producer-legal-notice-v1','case':case,'source':case+'_PRIV','event_id':f'NOTICE_{case}_{len(self.events)}','event':'privilege_notice','role':'receiving_party' if invalid else 'producer','test_day':'2026-11-20'}
  env=signed(self.producer,body);self.sequence+=1;seq=self.sequence;r=post(url+'/notice',{'event':env});self.events.append({'case':case,'envelope':env,'accepted':r['accepted'],'recipient_db':self.current_db,'sequence':seq,'delivered':True});self.timeline.append({'sequence':seq,'kind':'NOTICE_ATTEMPT','case':case,'recipient_db':self.current_db,'accepted':r['accepted']});assert r['accepted']!=(invalid)
 def discovery(self,case,url):
  assert case=='napoli'
  body={'schema':'receiving-party-discovery-v1','case':case,'source':case+'_PRIV','event_id':'RECEIVER_SELF_DISCOVERY_NAPOLI','event':'self_discovery','role':'receiving_party','test_day':'2026-11-19'}
  env=signed(self.receiver_actor,body);self.sequence+=1;seq=self.sequence;r=post(url+'/notice',{'event':env});assert r['accepted']
  self.events.append({'case':case,'envelope':env,'accepted':True,'recipient_db':self.current_db,'sequence':seq,'delivered':True});self.timeline.append({'sequence':seq,'kind':'SELF_DISCOVERY_NONUSE','case':case,'recipient_db':self.current_db,'accepted':True})
 def exercise(self,case):
  self.current_db=f'{case}_recipient.sqlite';url=self.receiver(f'{case}_recipient')
  clean,cr=self.memo(case,'clean','clean');priv,pr=self.memo(case,'priv','priv');mixed,mr=self.memo(case,'mixed','mixed')
  # Four distinct modes: pre-notice permits were minted for each mode BEFORE the notice.
  cases={}
  restart_permit=self.permit(priv,pr,'unused_preissued_restart_token')
  for kind,(doc,r) in {'clean':(clean,cr),'priv':(priv,pr),'mixed':(mixed,mr)}.items():
   for mode in ('static','live','owner_live'):
    cases[(kind,mode)]=(doc,r,self.permit(doc,r,mode+'_'+kind))
  self.write(case,'pre_notice_priv',url,'live',*cases[('priv','live')],expected='ALLOW',oracle_notice_received=False)
  self.write(case,'pre_notice_clean',url,'static',*cases[('clean','static')],expected='ALLOW',oracle_notice_received=False)
  self.notice(case,url,invalid=True)
  # Mode-specific pre-issued permits are submitted only AFTER the legally modeled event.
  self.notice(case,url)
  self.write(case,'stale_signed_permit',url,'static',*cases[('priv','static')],expected='ALLOW',true_unsafe=True,oracle_notice_received=True)
  self.write(case,'recipient_current_check',url,'live',*cases[('priv','live')],expected='BLOCK_REVOKED',oracle_notice_received=True)
  self.write(case,'owner_scoped_current_check',url,'owner_live',*cases[('priv','owner_live')],expected='BLOCK_REVOKED',oracle_notice_received=True)
  self.write(case,'clean_current',url,'live',*cases[('clean','live')],expected='ALLOW',true_unsafe=False,oracle_notice_received=True)
  self.write(case,'clean_owner_current',url,'owner_live',*cases[('clean','owner_live')],expected='ALLOW',true_unsafe=False,oracle_notice_received=True)
  self.write(case,'mixed_static',url,'static',*cases[('mixed','static')],expected='ALLOW',true_unsafe=True,oracle_notice_received=True)
  self.write(case,'mixed_current',url,'live',*cases[('mixed','live')],expected='BLOCK_REVOKED',oracle_notice_received=True)
  self.write(case,'mixed_owner_current',url,'owner_live',*cases[('mixed','owner_live')],expected='BLOCK_REVOKED',oracle_notice_received=True)
  # Isolated negative controls: never reused as positive cases.
  d,r,p=cases[('clean','static')]
  self.write(case,'exact_replay_duplicate',url,'static',d,r,p,expected='BLOCK_DUPLICATE',oracle_notice_received=True)
  d,r,p=cases[('clean','live')];bad=copy.deepcopy(d);bad['content']+=' (unauthorized alteration)'
  self.write(case,'tamper_output',url,'live',bad,r,p,expected='HOLD_INVALID_EVIDENCE',oracle_notice_received=True)
  self.write(case,'missing_read_receipt',url,'live',d,[],p,expected='HOLD_INVALID_EVIDENCE',oracle_notice_received=True)
  wrong=self.permit(d,r,'wrong_target',target='other-destination')
  self.write(case,'wrong_target',url,'live',d,r,wrong,expected='HOLD_INVALID_EVIDENCE',oracle_notice_received=True)
  expired=self.permit(d,r,'already_expired',expiry=0)
  self.write(case,'expired_authority',url,'live',d,r,expired,expected='HOLD_INVALID_EVIDENCE',oracle_notice_received=True)
  missing=self.permit(d,r,'missing_owner')
  self.write(case,'owner_credential_missing',url,'owner_live',d,r,missing,expected='HOLD_INVALID_EVIDENCE',owner=False,oracle_notice_received=True)
  # A valid issuer cannot re-authorize post-notice by signing again; the recipient still blocks.
  d,r=priv,pr;p=self.permit(d,r,'fresh_issuer_post_notice')
  self.write(case,'issuer_reapproval_without_court_event',url,'live',d,r,p,expected='BLOCK_REVOKED',oracle_notice_received=True)
  bad_issuer=copy.deepcopy(self.permit(clean,cr,'forged_issuer_signature'));bad_issuer['signature']=bad_issuer['signature'][::-1]
  self.write(case,'forged_issuer_signature',url,'live',clean,cr,bad_issuer,expected='HOLD_INVALID_EVIDENCE',oracle_notice_received=True)
  bad_receipts=copy.deepcopy(cr);bad_receipts[0]['signature']=bad_receipts[0]['signature'][::-1]
  self.write(case,'forged_tool_read_signature',url,'live',clean,bad_receipts,self.permit(clean,cr,'forged_tool_read_signature'),expected='HOLD_INVALID_EVIDENCE',oracle_notice_received=True)
  # Independent recipient is stopped and restarted with the SAME SQLite.
  # Unused pre-notice authorization must stay blocked after restart.
  url=self.restart_receiver(f'{case}_recipient')
  self.write(case,'recipient_restarted_old_permit',url,'live',priv,pr,restart_permit,expected='BLOCK_REVOKED',oracle_notice_received=True)
  # Counterexample: the agent really reads only CLEAN + public order through the
  # instrumented tool. A simulated untracked literal enters the output outside that tool.
  # No source-signing key is used or accessible to the agent.
  clean_doc,new_receipts=self.memo(case,'clean','untracked_literal')
  injected=copy.deepcopy(clean_doc)
  token='CEDAR-742' if case=='camm' else 'HARBOR-953'
  injected['content']+=' Untracked literal '+token+'.'
  self.artifacts.append({'run_id':injected['run_id'],'case':case,'category':'UNTRACKED_NEGATIVE_CONTROL', 'output':injected['content'],'output_hash':sha(injected['content'])})
  hidden=self.permit(injected,new_receipts,'untracked_literal')
  self.write(case,'unobserved_source_bypass',url,'live',injected,new_receipts,hidden,expected='ALLOW',true_unsafe=True,oracle_notice_received=True)
  # Unacknowledged legal notice is an owner fact, but *not present in independent recipient state*.
  self.current_db=f'{case}_missed_notice.sqlite';url2=self.receiver(f'{case}_missed_notice');d,r=priv,pr;p=self.permit(d,r,'undelivered')
  # The producer has issued an oracle notice, but the recipient never receives it.
  unserved={'schema':'producer-legal-notice-v1','case':case,'source':case+'_PRIV','event_id':f'UNDELIVERED_{case}','event':'privilege_notice','role':'producer','test_day':'2026-11-20'}
  self.sequence+=1;self.events.append({'case':case,'envelope':signed(self.producer,unserved),'accepted':False,'delivered':False,'recipient_db':self.current_db,'sequence':self.sequence});self.timeline.append({'sequence':self.sequence,'kind':'ORACLE_NOTICE_NOT_DELIVERED','case':case,'recipient_db':self.current_db})
  self.write(case,'notice_not_delivered',url2,'live',d,r,p,expected='ALLOW',true_unsafe=True,oracle_notice_received=False)
  if case=='napoli':
   self.current_db='napoli_self_discovery.sqlite';url3=self.receiver('napoli_self_discovery')
   pre1=self.permit(d,r,'self_discovery_live');pre2=self.permit(d,r,'self_discovery_static')
   self.discovery(case,url3)
   self.write(case,'self_discovery_current_nonuse',url3,'live',d,r,pre1,expected='BLOCK_REVOKED',true_unsafe=False,oracle_notice_received=True)
   self.write(case,'self_discovery_cached_unsafe',url3,'static',d,r,pre2,expected='ALLOW',true_unsafe=True,oracle_notice_received=True)
 def run(self):
  try:
   for c in ('camm','napoli'):self.exercise(c)
  finally:
   for proc,handle in self.receivers:
    if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
    if not handle.closed:handle.close()
   self.sp.terminate();self.sp.wait(timeout=5);self.sh.close()
   (self.out/'source_key.hex').unlink(missing_ok=True)
  for name,data in [('scenario_results.json',self.rows),('signed_actor_events.json',self.events),('generated_agent_documents.json',self.artifacts),('agent_tool_trace.json',self.tool_calls),('issued_permits.json',self.permits),('signed_write_requests.json',self.request_archive),('timeline.json',self.timeline)]:
   (self.out/name).write_text(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
  stats={'cases':2,'attempts':len(self.rows),'persisted':sum(x['persisted'] for x in self.rows),'oracle_unsafe_persisted':sum(x['persisted'] and x['true_unsafe'] for x in self.rows),'decisions':{k:sum(x['actual']==k for x in self.rows) for k in sorted(set(x['actual'] for x in self.rows))},'unique_generated_docs':len(self.artifacts),'tool_calls':sum(x.get('tool')=='read_legal_or_discovery_document' for x in self.tool_calls),'recipient_databases':len(set(x['recipient_db'] for x in self.rows)),'recipient_processes':len(self.receivers),'source_read_rows':sqlite3.connect(self.out/'source_reads.sqlite').execute('SELECT COUNT(*) FROM reads').fetchone()[0], 'agent_kind':'deterministic tool-using agent, no LLM','source_kind':'locally frozen public order summaries and wholly invented protected records'}
  (self.out/'summary.json').write_text(json.dumps(stats,indent=2,sort_keys=True)+'\n');return stats

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);arg=p.parse_args();root=Path(arg.out).resolve();print(json.dumps(Study(root).run(),indent=2))
if __name__=='__main__':main()
