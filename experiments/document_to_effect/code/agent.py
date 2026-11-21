"""Tool-using deterministic document-processing agent, no LLM inference.
The source gateway records every observed document read and signs each receipt.
The agent synthesizes a short memo from read text rather than a fixed canned output.
"""
import re,urllib.parse
from common import get,sha

def produce(case,run_id,source_url,choice):
 selected=[case+'_ORDER']+[case+'_'+x for x in choice]
 read=[];receipts=[];events=[]
 for sid in selected:
  doc=get(f'{source_url}/read?case={urllib.parse.quote(case)}&source={urllib.parse.quote(sid)}&run={urllib.parse.quote(run_id)}')
  read.append((sid,doc['text']));receipts.append(doc['receipt'])
  events.append({'tool':'read_legal_or_discovery_document','source_id':sid,'sha256':sha(doc['text']),'receipt_id':doc['receipt']['body']['read_id']})
 law=read[0][1];facts=[]
 for sid,txt in read[1:]:
  marks=re.findall(r'\b(?:CEDAR|HARBOR|AURORA|ORION)-\d+\b',txt)
  if marks:facts.append(f'{sid}: document marker {marks[0]}')
  elif txt:facts.append(f'{sid}: '+ ' '.join(txt.split())[:70])
 # The output text is grounded in the read text, with a structured decision memo format.
 action='five-business-day clawback from producer notice' if ('five business days' in law or 'five (5) business days' in law) else ('seven-day return clock from producer notice' if 'seven-calendar-day' in law else 'unresolved legal clock')
 content=f'Agent-prepared legal work note ({case.upper()}). Public order: {action}. '+('Evidence reviewed: '+'; '.join(facts)+'. ' if facts else '')+'Only the cited source snapshots were reviewed; this note is not legal advice.'
 events.append({'operation':'synthesize_note','legal_rule':action,'output_sha256':sha(content),'result_bytes':len(content.encode())})
 return {'case':case,'run_id':run_id,'content':content},receipts,events
