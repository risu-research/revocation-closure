"""Build typed, source-located A0 IR from UNMODIFIED Stage N and Stage R files.

This is manual adjudication captured in inspectable code. It neither uses a legal LLM
nor claims to prove textual entailment or completeness of the court orders.
"""
from __future__ import annotations
import hashlib,json,csv,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

# Roles are adjudicated against the order clauses and labeled by kind.
# 'scope_only' is NOT a legal duty assigned to a person.
ROLES={
'IOTTIE-R26-RESTRICTION':'receiving_party','CAMM-R26-RESTRICTION':'receiving_party',
'NAPOLI-R26-RESTRICTION':'receiving_party','I-09-SOURCE':'receiving_party',
'I-09-CHALLENGE':'receiving_challenger','I-03-INSPECTION':'receiving_party',
'I-19-FINAL-DISPOSITION':'receiving_party','I-19-ARCHIVE':'receiving_counsel',
'C-20-SOURCE':'receiving_party','C-03-20-COPY-BRIDGE':'scope_only',
'C-11-FINAL-DISPOSITION':'receiving_party','C-11-ARCHIVE':'receiving_counsel',
'N-13-SOURCE':'receiving_party','N-13-SELF-DISCOVERY':'receiving_party',
'N-14-CHALLENGE':'receiving_party','N-10-FINAL':'receiving_party',
'N-11-ARCHIVE':'receiving_counsel','N-10-NO-IMPORT':'scope_only'}
# Distinguish rule's operational origin from the original source locator.
RELATIONS={
'C-03-20-COPY-BRIDGE':'copy_definition_scope',
'N-10-NO-IMPORT':'limited_clause_scope',
'I-09-CHALLENGE':'restricted_challenge',
'N-14-CHALLENGE':'restricted_challenge',
'I-19-ARCHIVE':'restricted_archive',
'C-11-ARCHIVE':'restricted_archive',
'N-11-ARCHIVE':'restricted_archive'}
# Explicit review list for clauses actually reopened in public Justia PDF screenshots.
# All other locators were retained from Stage N and earlier Stage M review; none
# are falsely promoted to a byte-range verified source quote.
REOPENED={'I-09-SOURCE','I-09-CHALLENGE','I-19-FINAL-DISPOSITION',
          'C-20-SOURCE','C-11-FINAL-DISPOSITION','N-13-SOURCE',
          'N-13-SELF-DISCOVERY','N-14-CHALLENGE','N-10-FINAL','N-11-ARCHIVE'}
SOURCE_SCOPE={
 'iottie':{'§9.2':'claim/procedure; producer log; narrow challenge copy',
           '§19':'post-termination disposition and limited retention'},
 'camm':{'§20':'post-notice privilege procedure and five-business-day duties',
         '§11(b)':'postcase confidential document disposition'},
 'napoli':{'§13':'notice-or-self-discovery hold; separate producer-notice clock',
           '§10':'final-disposition, derivatives, certification'},
}
OUT_OF_SCOPE=[
 {'case':'camm','clause':'§10','topic':'conditional AI-tool upload requirements',
  'source_url':'https://cases.justia.com/federal/district-courts/new-york/nysdce/1:2025cv01921/638232/38/0.pdf',
  'pdf_page_1based':[7,8],'status':'DISCOVERED_NOT_COMPILED','comment':'Additional confidentiality/AI processing duty; outside the eighteen selected revocation declarations'},
 {'case':'napoli','clause':'§9','topic':'restriction on uploading another party confidential material to open LLMs; platform deletion preparation',
  'source_url':'https://cases.justia.com/federal/district-courts/new-york/nysdce/1:2025cv02872/640129/37/0.pdf',
  'pdf_page_1based':[7],'status':'DISCOVERED_NOT_COMPILED','comment':'Not safe to assert whole-order A0 completeness'}]

def build():
 src=ROOT/'inputs/verified_clause_rules_original.json';cp=ROOT/'inputs/R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER_original.csv'
 orig=json.loads(src.read_text());assert len(orig['rules'])==18
 assert set(ROLES)=={r['id'] for r in orig['rules']}
 rules=[]
 for item in orig['rules']:
  rule=dict(item)
  rid=item['id'];role=ROLES[rid]
  rule['duty_actor']=role
  rule['rule_kind']=RELATIONS.get(rid,'scoped_operative_rule')
  rule['source_link']={'url':item['pdf'],'clause':item['clause'],'page_1based':item['pdf_page_1based'],
    'assessment':'REOPENED_PDF_PAGE_LOCATOR' if rid in REOPENED else 'RETAINED_STAGE_M_N_LOCATOR',
    'quote_span':'NOT_AVAILABLE_IN_PINNED_LOCAL_PDF',
    'meaning_entailment':'MANUAL_ADJUDICATION_NOT_FORMALLY_PROVEN'}
  rules.append(rule)
 duties=[]
 for row in csv.DictReader(cp.open(encoding='utf-8-sig',newline='')):
  assert row['unit'] in {'months','calendar_days','business_days'}
  dr={'id':row['stage_n_rule_id'] or ('I-09-PRODUCER-LOG-10BD' if row['case']=='iottie' else 'N-10-CERTIFICATION-10CD'),
      'case':row['case'],'clause':row['clause'],'trigger':row['clock_start'],
      'actor':row['duty_bearer'],'action':row['action'],'clock':{'start':row['clock_start'],'amount':int(row['amount']),'unit':row['unit']},
      'source_url':row['source_url'],'source_pages':row['pdf_page_1_based'],
      'stage_n_implementation':row['implementation_status'],
      'source_review':'SAMPLED_ORDER_PAGE_REVIEWED','meaning_review':'MANUAL_RULE_MAPPING',
      'effect_type':'OBLIGATION_CLOCK_RECORD_ONLY'}
  if row['case']=='napoli' and row['action']=='written_confirmation_letter':dr['exception_gate']='requires_recorded_return_or_destruction'
  if row['case']=='iottie' and row['action']=='file_challenge_or_dispose_reserved_copy':dr['exception_gate']='single_restricted_challenge_copy'
  duties.append(dr)
 assert len(duties)==8
 repairs=[{'kind':'ADD_DUTY','id':'I-09-PRODUCER-LOG-10BD','status':'MODELED_IN_STAGE_R_NOT_IN_STAGE_N'},
          {'kind':'PATCH_CLOCK_METADATA','id':'N-10-FINAL','status':'MISSING_STAGE_N_DEADLINE'},
          {'kind':'ADD_DUTY','id':'N-10-CERTIFICATION-10CD','status':'MODELED_IN_STAGE_R_NOT_IN_STAGE_N'}]
 pack={'schema':'source-located-a0-assurance-ir-v1','scope':'eighteen original Stage N declarations plus eight selected Stage R duties',
       'original_hashes':{'stage_n':sha(src),'stage_r_duties':sha(cp)},
       'legal_source_disclaimer':'Only source page locators are retained; original PDFs are not pinned by local byte hash; a source locator is not proof of legal entailment.',
       'rules':rules,'duties':duties,'repairs':repairs,'outside_selected_scope':OUT_OF_SCOPE,
       'active_policy_mode':'TRUSTED_MANUAL_MAPPING_AND_STRUCTURAL_CHECKS'}
 out=ROOT/'inputs/a0_typed_policy.json';out.write_text(json.dumps(pack,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
 return pack
if __name__=='__main__':
 p=build();print(json.dumps({'rule_count':len(p['rules']),'duty_count':len(p['duties']),'repairs':len(p['repairs']),'bundle':str(ROOT/'inputs/a0_typed_policy.json')},indent=2))
