"""Independent structural A0 assurance + live recipient gate.

This module checks frozen originals, role/trigger/clock completeness, and limits.
It DOES NOT prove that an official court order semantically entails a policy rule.
Only signed, receiver-visible source reads and receiver-acknowledged events are in scope.
"""
from __future__ import annotations
import csv,hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
PINNED_N='1b302e6eefaa5e3b68b1f31b352fc89d400de272e3e8f4b38ebf6bafdc525934'
PINNED_R='693ba4be4385873a39b038266b11869fccedc74f11398b8765f1eb10f57624cf'
KNOWN_ROLES={
'IOTTIE-R26-RESTRICTION':'receiving_party','CAMM-R26-RESTRICTION':'receiving_party',
'NAPOLI-R26-RESTRICTION':'receiving_party','I-09-SOURCE':'receiving_party',
'I-09-CHALLENGE':'receiving_challenger','I-03-INSPECTION':'receiving_party',
'I-19-FINAL-DISPOSITION':'receiving_party','I-19-ARCHIVE':'receiving_counsel',
'C-20-SOURCE':'receiving_party','C-03-20-COPY-BRIDGE':'scope_only',
'C-11-FINAL-DISPOSITION':'receiving_party','C-11-ARCHIVE':'receiving_counsel',
'N-13-SOURCE':'receiving_party','N-13-SELF-DISCOVERY':'receiving_party',
'N-14-CHALLENGE':'receiving_party','N-10-FINAL':'receiving_party',
'N-11-ARCHIVE':'receiving_counsel','N-10-NO-IMPORT':'scope_only'}

def hfile(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def validate(bundle:dict, root=ROOT)->list[str]:
    """Separate compiler audit; deliberately not imported from build_a0_ir."""
    issues=[]
    nfile=root/'inputs/verified_clause_rules_original.json'
    rfile=root/'inputs/R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER_original.csv'
    if hfile(nfile)!=PINNED_N:issues.append('BASELINE_STAGE_N_BYTES_CHANGED')
    if hfile(rfile)!=PINNED_R:issues.append('BASELINE_STAGE_R_CLOCK_BYTES_CHANGED')
    if not isinstance(bundle,dict) or bundle.get('schema')!='source-located-a0-assurance-ir-v1':return issues+['BAD_IR_SCHEMA']
    if bundle.get('original_hashes')!={'stage_n':hfile(nfile),'stage_r_duties':hfile(rfile)}:issues.append('DECLARED_SOURCE_HASH_MISMATCH')
    raw=json.loads(nfile.read_text())['rules'];baseline={x['id']:x for x in raw}
    rules=bundle.get('rules',[])
    if not isinstance(rules,list) or len(rules)!=18:issues.append('EXPECTED_EXACTLY_18_ORIGINAL_RULES');rules=rules if isinstance(rules,list) else []
    seen=set()
    for r in rules:
        if not isinstance(r,dict):issues.append('MALFORMED_RULE');continue
        rid=r.get('id')
        if rid in seen:issues.append('DUPLICATE_RULE:'+str(rid))
        seen.add(rid)
        if rid not in baseline:issues.append('UNKNOWN_RULE:'+str(rid));continue
        original=baseline[rid]
        if {k:r.get(k) for k in original}!=original:issues.append('SOURCE_RULE_CHANGED:'+rid)
        if r.get('duty_actor')!=KNOWN_ROLES[rid]:issues.append('BAD_DUTY_ACTOR:'+rid)
        link=r.get('source_link',{})
        if not isinstance(link,dict) or (link.get('url'),link.get('clause'),link.get('page_1based'))!=(original['pdf'],original['clause'],original['pdf_page_1based']):issues.append('BAD_SOURCE_LOCATOR:'+rid)
        if r.get('rule_kind')=='copy_definition_scope' and r.get('duty_actor')!='scope_only':issues.append('SCOPE_INCORRECTLY_ASSIGNED_DUTY:'+rid)
    if seen!=set(baseline):issues.append('RULE_IDS_DO_NOT_MATCH_ORIGINALS')
    with rfile.open(encoding='utf-8-sig',newline='') as f:legacy=list(csv.DictReader(f))
    duties=bundle.get('duties',[])
    if not isinstance(duties,list) or len(duties)!=8:issues.append('REQUIRE_ALL_8_SELECTED_CLOCKS');duties=duties if isinstance(duties,list) else []
    expected=[]
    for row in legacy:
        rid=row['stage_n_rule_id'] or ('I-09-PRODUCER-LOG-10BD' if row['case']=='iottie' else 'N-10-CERTIFICATION-10CD')
        expected.append((rid,row))
    ids=[d.get('id') for d in duties if isinstance(d,dict)]
    if len(ids)!=len(set(ids)):issues.append('DUPLICATE_CLOCK_ID')
    for rid,row in expected:
        d=next((x for x in duties if isinstance(x,dict) and x.get('id')==rid),None)
        if d is None:issues.append('MISSING_DUTY:'+rid);continue
        expectedclock={'start':row['clock_start'],'amount':int(row['amount']),'unit':row['unit']}
        check={'case':row['case'],'clause':row['clause'],'trigger':row['clock_start'],
           'actor':row['duty_bearer'],'action':row['action'],'clock':expectedclock,
           'source_url':row['source_url'],'source_pages':row['pdf_page_1_based']}
        for k,v in check.items():
            if d.get(k)!=v:issues.append('DUTY_FIELD_CHANGED:'+rid+':'+k)
        if d.get('effect_type')!='OBLIGATION_CLOCK_RECORD_ONLY':issues.append('DUTY_SCOPE_ESCALATION:'+rid)
        if rid=='N-10-CERTIFICATION-10CD' and d.get('exception_gate')!='requires_recorded_return_or_destruction':issues.append('MISSING_COMPLETION_TRIGGER')
        if rid=='I-09-CHALLENGE' and d.get('exception_gate')!='single_restricted_challenge_copy':issues.append('CHALLENGE_COPY_SCOPE_WIDENED')
    if set(ids)!={rid for rid,_ in expected}:issues.append('CLOCK_SET_MISMATCH')
    omitted=bundle.get('outside_selected_scope',[])
    if not isinstance(omitted,list) or {(x.get('case'),x.get('clause')) for x in omitted if isinstance(x,dict)}!={('camm','§10'),('napoli','§9')}:
        issues.append('SCOPE_DISCLOSURE_MISSING')
    return sorted(set(issues))

class A0Gate:
    """Receiver-owned narrow gate applied in the SQL transaction before write.

    `source_type` originates from signed read receipts, but this synthetic model
    cannot attest that all external reads were captured. Missing notices also
    remain an independent failure boundary.
    """
    def __init__(self, path=None):
        path=pathlib.Path(path) if path else ROOT/'inputs/a0_typed_policy.json'
        self.path=path
        self.bundle=json.loads(path.read_text())
        self.issues=validate(self.bundle)
        self.policy_sha256=hfile(path)
        # Localized errors do not stop independently clean workflows or other cases.
        self.global_issues=[]
        self.case_issues={c:[] for c in ('iottie','camm','napoli')}
        original_rules={r['id']:r['case'] for r in self.bundle.get('rules',[]) if isinstance(r,dict)}
        original_duties={d['id']:d['case'] for d in self.bundle.get('duties',[]) if isinstance(d,dict)}
        missing_special={'I-09-PRODUCER-LOG-10BD':'iottie','N-10-CERTIFICATION-10CD':'napoli'}
        aggregate_inferred=any(x.startswith('MISSING_DUTY:') for x in self.issues)
        for issue in self.issues:
            if aggregate_inferred and issue in {'REQUIRE_ALL_8_SELECTED_CLOCKS','CLOCK_SET_MISMATCH'}:
                continue  # The specific MISSING_DUTY identifies the affected case.
            parts=issue.split(':')
            rid=parts[1] if len(parts)>1 else None
            case=original_rules.get(rid) or original_duties.get(rid) or missing_special.get(rid)
            if issue=='CHALLENGE_COPY_SCOPE_WIDENED':case='iottie'
            if case in self.case_issues:self.case_issues[case].append(issue)
            else:self.global_issues.append(issue)
    def decide(self,case,source_receipts,revoked,mode):
        if case not in ('camm','napoli','iottie'):
            return 'HOLD_A0_UNKNOWN_CASE'
        protected=[]
        for env in source_receipts:
            b=env.get('body',{})
            # Signed upstream read receipt is separately verified by the original Stage S code.
            if b.get('source_type')=='synthetic_protected':
                if b.get('source_id')!=case+'_PRIV':return 'HOLD_A0_SOURCE_CLASSIFICATION'
                protected.append(b.get('source_id'))
            elif b.get('source_id')==case+'_PRIV':return 'HOLD_A0_SOURCE_CLASSIFICATION'
        if protected and (self.global_issues or self.case_issues[case]):
            return 'HOLD_A0_UNVERIFIED_POLICY'
        if protected and mode=='static' and set(protected).intersection(revoked):
            return 'BLOCK_A0_REVOKED'
        return None

if __name__=='__main__':
    b=json.loads((ROOT/'inputs/a0_typed_policy.json').read_text());print(json.dumps({'issues':validate(b),'rule_count':len(b['rules']),'duty_count':len(b['duties'])},indent=2))
