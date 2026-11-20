#!/usr/bin/env python3
"""Read-only SQLite + frozen oracle auditor, independent of receiver policy code.
Does not import effect_receiver.py or generic_policy_extractor.py.
"""
from pathlib import Path
import json,csv,hashlib,hmac,sqlite3,argparse,collections
R=Path(__file__).resolve().parents[1]
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def js(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def frozen_check():
 for name in ('FROZEN_SHA256.json','FROZEN_SCENARIOS_SHA256.json'):
  for path,sha in json.loads((R/'gold'/name).read_text()).items():
   assert hashlib.sha256((R/path).read_bytes()).hexdigest()==sha,('FROZEN_INPUT_TAMPER',path)
def audit_folder(f):
 keys=json.loads((f/'keys_private_test_only.json').read_text());secret=bytes.fromhex(keys['token_secret'])
 con=sqlite3.connect('file:'+str((f/'recipient.sqlite').resolve())+'?mode=ro',uri=True)
 assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 cases={x['scenario_id']:x for x in csv.DictReader((R/'gold/scenario_oracle.csv').open())}
 rows=con.execute('SELECT scenario_id,case_id,mode,permit_id,decision,reason,visible_event,source_kind,requested_effect,actor,content_sha256,content FROM attempts ORDER BY id').fetchall()
 cols=['scenario_id','case_id','mode','permit_id','decision','reason','visible_event','source_kind','requested_effect','actor','content_sha256','content']
 attempts=[dict(zip(cols,r)) for r in rows]
 assert set(a['scenario_id'] for a in attempts)==set(cases) and len(attempts)==len(cases)
 effs=con.execute('SELECT scenario_id,case_id,mode,content,content_sha256,permit_id FROM effects').fetchall()
 effects={r[0]:r for r in effs};assert len(effects)==len(effs)
 permits={r[0]:r for r in con.execute('SELECT permit_id,case_id,body,signature,issue_epoch FROM permits')}
 assert len(permits)==len(cases)
 notices=collections.defaultdict(list)
 for scenario,case,event in con.execute('SELECT scenario_id,case_id,event FROM notices ORDER BY id'):
  assert scenario in cases and case==cases[scenario]['case_id'];notices[scenario].append(event)
 mode=(f.name)
 summary={'mode':mode,'attempts':len(attempts),'physical_effects':len(effects),'correct_all':0,'false_allow':0,'false_hold_or_block':0,
          'expected_legal_blocks':0,'expected_legal_allows':0,'false_allow_ids':[],'false_hold_ids':[],'decisions':dict(collections.Counter(x['decision'] for x in attempts))}
 for a in attempts:
  sc=cases[a['scenario_id']];sid=a['scenario_id'];p=permits[a['permit_id']]
  obj=json.loads(p[2]);want=hmac.new(secret,js(obj),hashlib.sha256).hexdigest()
  assert hmac.compare_digest(want,p[3]),('ISSUE_SIGNATURE_BAD',sid)
  assert obj['issue_epoch']==0 and p[4]==0,('TOKEN_NOT_PREISSUED',sid)
  assert obj['permit_id']==a['permit_id'] and obj['scenario_id']==sid and p[1]==sc['case_id']
  assert obj['content_sha256']==a['content_sha256']==h(a['content']),('CONTENT_BINDING_BAD',sid)
  assert a['source_kind']==obj['source_kind']==sc['source_kind']
  assert a['actor']==obj['actor']==sc['actor']
  assert a['requested_effect']==obj['effect']==sc['requested_effect']
  assert a['case_id']==obj['case_id']==sc['case_id']
  expected_notice=[] if sc['receiver_notice']=='recipient_uninformed' or sc['real_event']=='pre_notice' else [sc['real_event']]
  assert notices[sid]==expected_notice and a['visible_event']==(expected_notice[-1] if expected_notice else None),('NOTICE_HISTORY_BAD',sid)
  persisted=(sid in effects)
  assert (a['decision']=='ALLOW')==persisted,('DECISION_EFFECT_MISMATCH',sid)
  if persisted:
    e=effects[sid]
    assert (e[1],e[2],e[3],e[4],e[5])==(sc['case_id'],mode,a['content'],h(a['content']),a['permit_id']),('EFFECT_BYTES_BAD',sid)
  if sc['expected']=='ALLOW':summary['expected_legal_allows']+=1
  else:summary['expected_legal_blocks']+=1
  if (sc['expected']=='ALLOW')==persisted:summary['correct_all']+=1
  elif persisted:summary['false_allow']+=1;summary['false_allow_ids'].append(sid)
  else:summary['false_hold_or_block']+=1;summary['false_hold_ids'].append(sid)
 return summary
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--folder',required=True);ap.add_argument('--out');a=ap.parse_args();frozen_check()
 results=[audit_folder(Path(a.folder)/name) for name in ('static','gated')]
 out={'schema':'independent-physical-effects-audit-v1','results':results}
 if a.out:Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out,indent=2))
