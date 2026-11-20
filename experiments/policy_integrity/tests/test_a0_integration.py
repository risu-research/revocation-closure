"""Run independent corrupted-policy and persisted-SQL tests on original signed Stage S requests.

The tester never calls the recipient's policy decision function, and reads the
physical SQLite files after the HTTP process has stopped. It uses preserved
Stage S signed requests as a replay fixture rather than forging new credentials.
"""
from __future__ import annotations
import copy,hashlib,json,os,pathlib,random,socket,sqlite3,subprocess,sys,tempfile,time,unittest,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from a0_assurance import validate
BASE=json.loads((ROOT/'inputs/a0_typed_policy.json').read_text())
RUN=ROOT/'results/stage_s_baseline_rerun'
SOURCE=ROOT/'stage_s_hardened/code/recipient_server.py'
ORIGINAL=ROOT/'inputs/STAGE_S_RECIPIENT_original.py'
# Original server expects common.py in its own directory; reuse original package path.
ORIGINAL=ROOT/'stage_s_original/code/recipient_server.py'

def make_mutations():
 def change_actor(x):x['rules'][8]['duty_actor']='producing_party'
 def drop_actor(x):del x['rules'][8]['duty_actor']
 def changed_clock(x):next(d for d in x['duties'] if d['id']=='C-20-SOURCE')['clock']['unit']='calendar_days'
 def delete_clock(x):x['duties']=[d for d in x['duties'] if d['id']!='C-20-SOURCE']
 def change_time_anchor(x):next(d for d in x['duties'] if d['id']=='N-13-SOURCE')['clock']['start']='self_discovery'
 def miss_napoli_final(x):x['duties']=[d for d in x['duties'] if d['id']!='N-10-FINAL']
 def miss_napoli_confirmation(x):x['duties']=[d for d in x['duties'] if d['id']!='N-10-CERTIFICATION-10CD']
 def weaken_challenge(x):next(d for d in x['duties'] if d['id']=='I-09-CHALLENGE')['exception_gate']='any_number_of_unrestricted_copies'
 def wrong_source(x):next(r for r in x['rules'] if r['id']=='C-20-SOURCE')['source_link']['url']='https://example.invalid/other.pdf'
 def change_source_rule(x):next(r for r in x['rules'] if r['id']=='C-20-SOURCE')['events']=['FINAL_TERMINATION']
 def drop_rule(x):x['rules']=[r for r in x['rules'] if r['id']!='C-20-SOURCE']
 def hide_ai_exception(x):x['outside_selected_scope']=[]
 def escalation(x):next(d for d in x['duties'] if d['id']=='N-13-SOURCE')['effect_type']='ALLOW_ANY_WRITE'
 return dict(wrong_actor=change_actor,missing_actor=drop_actor,wrong_business_day=changed_clock,
         missing_camm_clock=delete_clock,wrong_notice_clock=change_time_anchor,
         missing_napoli_30d=miss_napoli_final,missing_confirmation_10d=miss_napoli_confirmation,
         challenge_copy_escalation=weaken_challenge,source_locator_swap=wrong_source,
         source_rule_semantic_mutation=change_source_rule,deleted_stage_n_rule=drop_rule,
         undisclosed_ai_scope=hide_ai_exception,clock_permission_escalation=escalation)

def freeport():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def post(url,data):
 payload=json.dumps(data).encode();req=urllib.request.Request(url,data=payload,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=3) as r:return json.load(r)

def run_receiver(policyfile, case, folder, *, old=False):
 folder.mkdir(parents=True,exist_ok=True)
 port=freeport();dbpath=folder/'effects.sqlite'
 target=ORIGINAL if old else SOURCE
 env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
 if policyfile:env['A0_POLICY_PATH']=str(policyfile)
 proc=subprocess.Popen([sys.executable,str(target),'--port',str(port),'--db',str(dbpath),'--trust',str(RUN/'trust.json')],
    cwd=str(target.parent),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=env)
 url=f'http://127.0.0.1:{port}'
 try:
  for _ in range(100):
   if proc.poll() is not None:raise RuntimeError('receiver failed '+proc.stderr.read().decode()[:500])
   try:
    with urllib.request.urlopen(url+'/ping',timeout=.2) as r:
     if json.load(r).get('ok'):break
   except Exception:time.sleep(.03)
  else:raise RuntimeError('receiver not ready')
  saved=json.loads((RUN/'signed_write_requests.json').read_text())
  responses={}
  for name in ('pre_notice_priv','pre_notice_clean'):
   req=next(x['request'] for x in saved if x['case']==case and x['scenario']==name)
   responses[name]=post(url+'/write',req)
 finally:
  proc.terminate()
  try:proc.communicate(timeout=5)
  except subprocess.TimeoutExpired:proc.kill();proc.communicate()
 db=sqlite3.connect(dbpath)
 effects=db.execute('SELECT run_id,mode,content_sha256 FROM effects ORDER BY id').fetchall()
 attempts=db.execute('SELECT decision,run_id FROM attempts ORDER BY id').fetchall()
 chk=db.execute('PRAGMA integrity_check').fetchone()[0];db.close()
 assert chk=='ok'
 return {'case':case,'pre_notice_priv':responses['pre_notice_priv']['decision'],
  'pre_notice_clean':responses['pre_notice_clean']['decision'],
  'stored_effects':len(effects),'effect_run_ids':[row[0] for row in effects],
  'physical_attempts':attempts}

def exercise():
 report={'schema':'a0-mutation-and-real-effect-test-v1','mutations':[],'controls':{}}
 with tempfile.TemporaryDirectory(prefix='a0_neg_') as temp:
  tmp=pathlib.Path(temp)
  report['controls']['original_camm']=run_receiver(None,'camm',tmp/'original',old=True)
  report['controls']['hardened_camm']=run_receiver(ROOT/'inputs/a0_typed_policy.json','camm',tmp/'valid')
  assert report['controls']['original_camm']['stored_effects']==2
  assert report['controls']['hardened_camm']['stored_effects']==2
  report['controls']['hardened_napoli']=run_receiver(ROOT/'inputs/a0_typed_policy.json','napoli',tmp/'valid_napoli')
  assert report['controls']['hardened_napoli']['stored_effects']==2
  for name,mutate in make_mutations().items():
   packet=copy.deepcopy(BASE);mutate(packet)
   errors=validate(packet)
   assert errors,(name,'undetected mutation')
   p=tmp/(name+'.json');p.write_text(json.dumps(packet,indent=2))
   # Case-specific or shared fault. For iOttie-only exception there is no
   # iOttie Stage S signed request, so only structural validation is claimed.
   case='napoli' if 'napoli' in name or 'confirmation' in name or name=='wrong_notice_clock' or name=='clock_permission_escalation' else 'camm'
   if name=='challenge_copy_escalation':actual=None
   else:
    actual=run_receiver(p,case,tmp/(name+'_db'))
    assert actual['pre_notice_priv']=='HOLD_A0_UNVERIFIED_POLICY',(name,errors,actual)
    assert actual['pre_notice_clean']=='ALLOW',(name,actual)
    assert actual['stored_effects']==1,(name,actual)
   report['mutations'].append({'name':name,'case_tested':case if actual else None,
    'compiler_detected':True,'errors':errors,'physical_replay':actual})
 report['totals']={'injected_mutations':len(report['mutations']),'detected_by_compiler':len(report['mutations']),
     'mutations_tested_against_recipient':sum(x['physical_replay'] is not None for x in report['mutations']),
     'mutated_protected_source_writes_persisted':sum(int(x['physical_replay']['pre_notice_priv']=='ALLOW') for x in report['mutations'] if x['physical_replay']),
     'mutated_clean_source_writes_preserved':sum(int(x['physical_replay']['pre_notice_clean']=='ALLOW') for x in report['mutations'] if x['physical_replay'])}
 out=ROOT/'results/a0_mutation_results.json';out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 return report
if __name__=='__main__':
 data=exercise();print(json.dumps(data['totals'],indent=2))
