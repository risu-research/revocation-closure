#!/usr/bin/env python3
"""Held-out scoring. Unlike extractor, this file loads the frozen gold data."""
from pathlib import Path
import csv,json,hashlib,collections
from functools import lru_cache
R=Path(__file__).resolve().parents[1]
FIELDS=['actor','trigger','action','clock_unit','clock_amount','clock_start','exception']

def verify_hashes():
    for manifest in [R/'gold/FROZEN_SHA256.json',R/'gold/FROZEN_SCENARIOS_SHA256.json']:
        for name,sha in json.loads(manifest.read_text()).items():
            assert hashlib.sha256((R/name).read_bytes()).hexdigest()==sha,f'TAMPERED_FROZEN_INPUT:{name}'

def score():
    verify_hashes()
    gold=list(csv.DictReader((R/'gold/reference_duties.csv').open()))
    source=json.loads((R/'sources/scoped_order_passages.json').read_text())
    proposals=json.loads((R/'results/one_shot_policy_proposals.json').read_text())['proposals']
    for x in gold:x['clock_amount']=int(x['clock_amount'])
    groups=collections.defaultdict(lambda:[[],[]]);matches=[]
    for x in gold:groups[(x['case_id'],x['passage_id'])][0].append(x)
    for y in proposals:groups[(y['case_id'],y['passage_id'])][1].append(y)
    # maximum-score one-to-one matching by passage, with a match ONLY if action category agrees
    # (avoids presenting a unrelated fragment as a correctly extracted obligation).
    for key,(gs,ps) in groups.items():
        available=set(range(len(ps)))
        for g in gs:
            options=[(sum(g[k]==ps[j][k] for k in FIELDS),j) for j in available if g['action']==ps[j]['action']]
            if options:
                _,j=max(options);available.remove(j)
                matches.append({'id':g['id'],'case_id':key[0],'passage_id':key[1],'status':'action_detected',
                  'gold':{k:g[k] for k in FIELDS},'proposed':{k:ps[j][k] for k in FIELDS},
                  'field_matches':{k:g[k]==ps[j][k] for k in FIELDS}, 'proposal_id':ps[j]['candidate_id']})
            else:matches.append({'id':g['id'],'case_id':key[0],'passage_id':key[1],'status':'missed_action',
                  'gold':{k:g[k] for k in FIELDS},'proposal_id':None})
    matches=sorted(matches,key=lambda x:x['id'])
    recognized=[x for x in matches if x['status']=='action_detected']
    deadline=[x for x in matches if x['gold']['clock_unit'] in ('business_days','court_days','calendar_days')]
    summary={
      'gold_duties':len(gold),'source_passages':sum(len(x['passages']) for x in source['orders'].values()),
      'generated_fragments':len(proposals),'generated_with_missing_critical_fields':sum(x['proposal_status']=='UNRESOLVED' for x in proposals),
      'action_detected':len(recognized),'action_recall':round(len(recognized)/len(gold),4),
      'complete_tuple_correct':sum(all(x['field_matches'].values()) for x in recognized),
      'actor_correct_on_detected':sum(x['field_matches']['actor'] for x in recognized),
      'trigger_correct_on_detected':sum(x['field_matches']['trigger'] for x in recognized),
      'exceptions_correct_on_detected':sum(x['field_matches']['exception'] for x in recognized),
      'clock_bearing_duties':len(deadline),
      'clock_full_correct':sum(x.get('field_matches',{}).get('clock_unit',False) and x['field_matches']['clock_amount'] and x['field_matches']['clock_start'] for x in deadline),
      'cases': {case:{'gold':sum(x['case_id']==case for x in matches),'action_detected':sum(x['case_id']==case and x['status']=='action_detected' for x in matches)} for case in source['orders']},
      'important_note':'Proposal strings use source only, but authoring of generic patterns followed human gold construction; this is a fixed one-shot exploratory artifact-separated evaluation, not external blind predictive validation.'}
    (R/'results/extraction_scored.json').write_text(json.dumps({'summary':summary,'by_duty':matches},indent=2)+'\n')
    return summary
if __name__=='__main__':print(json.dumps(score(),indent=2))
