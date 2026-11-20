"""Compare original Stage S stored outcomes with Stage T, using saved real SQL traces."""
from __future__ import annotations
import collections,json,pathlib,sqlite3
ROOT=pathlib.Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'results/stage_s_baseline_rerun'
A0=ROOT/'results/a0_enforced_primary'
def load(where):
 summary=json.loads((where/'summary.json').read_text())
 rows=json.loads((where/'scenario_results.json').read_text())
 agent=json.loads((where/'generated_agent_documents.json').read_text())
 return summary,{(x['case'],x['scenario']):x for x in rows},agent

def go():
 os,ob,oa=load(ORIGINAL);ts,tb,ta=load(A0)
 assert len(ob)==len(tb)==46
 changes=[]
 for key,a in ob.items():
  b=tb[key]
  if a['actual']!=b['actual']:
   changes.append({'case':key[0],'scenario':key[1],'from':a['actual'],'to':b['actual'],
                   'oracle_unsafe_before':a['true_unsafe'],'oracle_unsafe_after':b['true_unsafe']})
  if not a['true_unsafe'] and a['persisted']:
   assert b['persisted'],('unexpected false block',key)
 assert len(changes)==5
 assert all(x['from']=='ALLOW' and x['to']=='BLOCK_A0_REVOKED' for x in changes)
 def count_safe(rows):return sum(x['persisted'] and not x['true_unsafe'] for x in rows.values())
 assert count_safe(ob)==count_safe(tb)==8
 assert os['oracle_unsafe_persisted']==9 and ts['oracle_unsafe_persisted']==4
 orig_camm=sum('unresolved legal clock' in x['output'] for x in oa if x['case']=='camm')
 new_camm=sum('unresolved legal clock' in x['output'] for x in ta if x['case']=='camm')
 assert orig_camm==5 and new_camm==0
 result={'baseline_total':46,'stage_t_total':46,'changed_decisions':changes,'changed_count':len(changes),
       'legitimate_persisted_original':count_safe(ob),'legitimate_persisted_stage_t':count_safe(tb),
       'unsafe_persisted_original':os['oracle_unsafe_persisted'],'unsafe_persisted_stage_t':ts['oracle_unsafe_persisted'],
       'camm_memos_unresolved_original':orig_camm,'camm_memos_unresolved_stage_t':new_camm,
       'comparison_scope':'Same fixed scenarios using fresh signed evidence and separate SQLite recipients; not a new held-out population.'}
 (ROOT/'results/baseline_to_stage_t_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':go()
