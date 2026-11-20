#!/usr/bin/env python3
"""Uses the same action-first exact seven-field matching as Phase A."""
import csv,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
F=['actor','trigger','action','clock_unit','clock_amount','clock_start','exception']
def main():
 manifest=json.loads((R/'SEAL_BEFORE_GENERATION.json').read_text())
 for name in ('new_gold.csv','new_order_passages.json'):
  assert hashlib.sha256((R/name).read_bytes()).hexdigest()==manifest[name]
 assert hashlib.sha256((R.parent/'src/generic_policy_extractor.py').read_bytes()).hexdigest()==manifest['frozen_extractor_sha256']
 raw=list(csv.DictReader((R/'new_gold.csv').open()))
 preds=json.loads((R/'one_shot_proposals.json').read_text())['proposals']
 rows=[];used=set()
 for g in raw:
  g['clock_amount']=int(g['clock_amount'])
  opts=[(sum(g[f]==p[f] for f in F),j) for j,p in enumerate(preds) if j not in used and g['passage_id']==p['passage_id'] and g['action']==p['action']]
  if opts:
   _,j=max(opts);used.add(j);p=preds[j]
   rows.append({'id':g['id'],'status':'action_detected','proposal':p['candidate_id'],'field_matches':{f:g[f]==p[f] for f in F}})
  else:rows.append({'id':g['id'],'status':'missed_action','proposal':None})
 matched=[x for x in rows if x['status']=='action_detected']
 summary={'confirmatory_new_order':'Ty v. Walmart Inc.','gold_duties':len(raw),'new_fragments':len(preds),'action_detected':len(matched),'full_tuples_correct':sum(all(x['field_matches'].values()) for x in matched),
  'extractor_source_sha256':manifest['frozen_extractor_sha256'],'note':'Extractor code hash was fixed before this additional court order was selected and its reference table created; no retraining or feedback tuning was performed.'}
 (R/'confirmatory_score.json').write_text(json.dumps({'summary':summary,'by_duty':rows},indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
