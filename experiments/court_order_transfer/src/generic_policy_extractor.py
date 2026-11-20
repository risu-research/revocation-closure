#!/usr/bin/env python3
"""One-shot, source-only deterministic clause proposal baseline.

This extractor loads ONLY sources/scoped_order_passages.json. It never reads gold.
Rules are generic legal-sentence lexical patterns, not code for particular cases.
Generated proposals are unverified, and no automatic 'legal validity' is claimed.
"""
from __future__ import annotations
import argparse,json,re,hashlib,pathlib
NUMBER={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'ten':10,'fourteen':14,'thirty':30,'sixty':60}

def fragments(text):
    # Split enumerated duties and sentence boundaries; preserve connecting text in its fragment.
    tmp=re.sub(r';\s*(?=\([ivx]+\))','\n',text,flags=re.I)
    tmp=re.sub(r'(?<=\.)\s+(?=[A-Z])','\n',tmp)
    tmp=re.sub(r';\s+(?=and\s+\(|\([a-z]\))','\n',tmp,flags=re.I)
    return [x.strip() for x in tmp.split('\n') if x.strip()]

def actor(text):
    t=text.lower()
    m=re.search(r'\b(producing party|disclosing party|designating party|receiving party|recipient|counsel|attorneys)\b.{0,90}?\b(shall|must|may|is entitled to|are entitled to)\b',t)
    if m:
        x=m.group(1)
        if x in ('producing party','disclosing party','designating party'):return 'producer'
        if x in ('counsel','attorneys'):return 'counsel'
        return 'recipient'
    return 'unknown'

def clock(text):
    t=text.lower()
    m=re.search(r'\bwithin\s+(?:(?:no more than|not later than)\s+)?(\d+|one|two|three|four|five|six|seven|ten|fourteen|thirty|sixty)\s*(?:\(\s*\d+\s*\)\s*)?(business|court|calendar)?\s*days?\b',t)
    if not m:
        m=re.search(r'\bno later than\s+(\d+|one|two|three|four|five|seven|ten|thirty|sixty)\s*(?:\(\s*\d+\s*\))?\s*(business|court|calendar)?\s*days?\b',t)
    if not m:
        if 'immediately' in t:return ['immediate',0,'none']
        if 'promptly' in t:return ['prompt',0,'none']
        if 'pending the ruling' in t or 'until the challenge is resolved' in t:return ['until_resolution',0,'none']
        if 'until further order' in t:return ['until_court_order',0,'none']
        return ['none',0,'none']
    n=int(m.group(1)) if m.group(1).isdigit() else NUMBER.get(m.group(1),0)
    unit={'business':'business_days','court':'court_days','calendar':'calendar_days',None:'calendar_days'}[m.group(2)]
    suffix=t[m.end():m.end()+110]
    prefix=t[max(m.start()-70,0):m.start()]
    if 'challenge notice' in suffix or 'challenge notice' in prefix and 'within' in t:return [unit,n,'challenge_notice']
    if 'certification' in suffix or 'certification' in prefix:return [unit,n,'return_or_destruction_certification']
    if 'final disposition' in suffix:return [unit,n,'final_disposition']
    if 'written request' in suffix or 'written request' in prefix:return [unit,n,'producer_written_request']
    if 'receipt of a request' in suffix or 'receipt of the request' in suffix:return [unit,n,'receipt_of_return_request']
    if 'of such request' in suffix:return [unit,n,'producer_written_request']
    return [unit,n,'unknown']

def action(text):
    t=text.lower()
    # General lexical actions used across legal orders, no names or section IDs.
    checks=[
      (r'privilege log','produce_privilege_log'),
      (r'sealed envelope|sequester','sealed_retention_no_use'),
      (r'archival copy','restricted_archival_retention'),
      (r'move the court|raise a challenge with the court','court_challenge'),
      (r'no more copies|retained copies','limited_challenge_retention'),
      (r'notify.*(?:receiving party).*?(?:in writing)|notifying the receiving party in writing','written_notice_and_request'),
      (r'notify.*counsel for the producing party','notify_producer_counsel'),
      (r'notify.*(?:party or person|transmitted)','notify_downstream_and_retrieve'),
      (r'no further examination or disclosure','stop_examination_disclosure'),
      (r'not use .*?until further order','suspend_use'),
      (r'(?:submit|provide).*?written certification|\bcertify\b|confirm that fact in writing','certify_final_disposition'),
      (r'destroyed.*?copies|copies.*?destroyed|shall be destroyed|expunged','destroy_copies_and_derivatives'),
      (r'return .*?or destroy|return all protected material','return_or_destroy_protected_material'),
      (r'return.*?inadvertent','return_claimed_material'),
      (r'return.*?confidential','return_confidential_material')]
    for rg,label in checks:
        if re.search(rg,t,re.S):return label
    return 'unknown'

def trigger(text):
    t=text.lower()
    if 'final disposition' in t and 'written request' in t:return 'final_disposition_plus_designator_written_request'
    if 'final disposition' in t:return 'final_disposition'
    if 'challenge notice' in t:return 'challenge_notice'
    if 'pending the ruling' in t:return 'pending_ruling'
    if 'upon written request' in t:return 'producer_written_request'
    if 'discovery' in t and 'upon request' in t:return 'self_discovery_or_request'
    if 'upon request' in t:return 'producer_written_request'
    if 'receipt of a request' in t:return 'receipt_of_return_request'
    if 'certification' in t and 'within' in t:return 'return_or_destruction_certification'
    return 'unknown'

def exception(text):
    t=text.lower()
    if 'no more copies' in t:return 'no_more_copies_than_needed'
    if 'unless' in t and 'challenge' in t:return 'timely_challenge'
    if 'upon permission' in t:return 'producer_permission_to_destroy'
    if 'archival copy' in t:return 'protected_archive'
    return 'none'

def generate(source):
    result=[]
    for case,doc in source['orders'].items():
        for p in doc['passages']:
            for idx,frag in enumerate(fragments(p['text'])):
                if len(frag)<24:continue
                cu,am,cs=clock(frag)
                obj={'candidate_id':f'{case}:{p["id"]}:{idx}','case_id':case,'passage_id':p['id'],
                   'actor':actor(frag),'trigger':trigger(frag),'action':action(frag),
                   'clock_unit':cu,'clock_amount':am,'clock_start':cs,'exception':exception(frag),
                   'evidence_excerpt':frag[:180]}
                obj['missing_critical_fields']=[k for k in ['actor','trigger','action'] if obj[k]=='unknown']
                if obj['clock_unit'] in ('calendar_days','business_days','court_days') and obj['clock_start']=='unknown':obj['missing_critical_fields'].append('clock_start')
                obj['proposal_status']='UNRESOLVED' if obj['missing_critical_fields'] else 'LEXICAL_ONLY_UNVERIFIED'
                result.append(obj)
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    src=pathlib.Path(args.source);dest=pathlib.Path(args.out)
    data=generate(json.loads(src.read_text()))
    dest.write_text(json.dumps({'schema':'source-only-lexical-proposals-v1','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'proposals':data},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'candidate_count':len(data),'unknown_candidates':sum(x['proposal_status']=='UNRESOLVED' for x in data),'output':str(dest)}))
