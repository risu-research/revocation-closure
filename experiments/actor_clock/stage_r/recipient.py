"""Stage R independent SQLite recipient, built on unmodified Stage N and Q validators.

The trust boundary is the receiving process and its BEGIN IMMEDIATE transaction.
Source/role/case registries are trusted synthetic fixtures. All legal dates are
recipient-recorded simulated dates, not client-submitted timestamps.
"""
from __future__ import annotations
import base64
import json
import sys
from pathlib import Path
from typing import Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from stage_r.law import load_duties,EVENT_ROLES,parsedate,evaluate_due,counterpart_completion,deadline,ROLES,TEST_CLOSED_DATES

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor_stage_q'))
from experiments.policy_compiler.verified_recipient import VerifiedRecipient,EvidenceError,verify,digest,stable_json
from experiments.trusted_transform.recipient_v2 import validate_v2

EVENT_FIELDS={'schema','event_id','case','event','source_id','role','sequence','nonce'}
AUTH_FIELDS={'schema','case','artifact_id','action','role','nonce'}

class LegalRecipient:
    def __init__(self, db: Path, trust: dict, clock_date: str, *, calendar_enabled=True):
        parsedate(clock_date)
        self.now=clock_date
        self.calendar_enabled=calendar_enabled
        self.closed_dates=TEST_CLOSED_DATES if calendar_enabled else None
        self.trust=trust
        broker=serialization.load_pem_public_key(trust['broker_public_key_pem'].encode())
        self.role_pubs={case:{role:serialization.load_pem_public_key(pem.encode()) for role,pem in roles.items()}
                        for case,roles in trust['role_pubkeys'].items()}
        self.gate=VerifiedRecipient(db,broker,{})
        self.db=self.gate.db
        self.duties=load_duties()
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS legal_events (
            event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, event_name TEXT NOT NULL,
            source_id TEXT, actor_role TEXT NOT NULL, sequence INTEGER NOT NULL,
            received_date TEXT NOT NULL, policy_epoch INTEGER NOT NULL, envelope TEXT NOT NULL,
            UNIQUE(case_id,actor_role,sequence));
        CREATE TABLE IF NOT EXISTS legal_effect_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, artifact_id TEXT NOT NULL,
            role TEXT, verdict TEXT NOT NULL, persisted INTEGER NOT NULL,
            policy_epoch INTEGER NOT NULL, clock_date TEXT NOT NULL, sources TEXT NOT NULL,
            reason TEXT NOT NULL, proof_sha256 TEXT NOT NULL, policy_digest TEXT NOT NULL,
            bundle_json TEXT NOT NULL, actor_envelope_json TEXT NOT NULL,
            declared_sources_json TEXT NOT NULL, client_cached_approval INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS legal_effects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER NOT NULL UNIQUE,
            case_id TEXT NOT NULL, artifact_id TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
            policy_epoch INTEGER NOT NULL, clock_date TEXT NOT NULL,
            FOREIGN KEY(attempt_id) REFERENCES legal_effect_attempts(id));
        CREATE TABLE IF NOT EXISTS legal_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, note_id TEXT NOT NULL UNIQUE,
            qualified_counsel_attested INTEGER NOT NULL, policy_epoch INTEGER NOT NULL,
            reuse_blocked INTEGER NOT NULL DEFAULT 1, actor_envelope_json TEXT NOT NULL,
            trusted_facts_digest TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS legal_challenge_copy (
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, source_id TEXT NOT NULL,
            challenge_role TEXT NOT NULL, reserved_epoch INTEGER NOT NULL, reserved_date TEXT NOT NULL,
            restriction TEXT NOT NULL, actor_envelope_json TEXT NOT NULL,
            UNIQUE(case_id,source_id));
        CREATE TABLE IF NOT EXISTS legal_rejections (
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, event_or_artifact TEXT,
            reason TEXT NOT NULL, policy_epoch INTEGER NOT NULL, date TEXT NOT NULL);
        ''')
        for case,sid,sh in trust['pinned_source_digests']:
            self.db.execute('INSERT OR IGNORE INTO sources(case_id,source_id,source_sha256) VALUES(?,?,?)',(case,sid,sh))

    def set_clock_trusted(self, v: str):
        parsedate(v)
        if v<self.now:raise EvidenceError('Trusted simulated clock must be monotone')
        self.now=v

    def set_calendar_trusted(self, enabled:bool):
        if type(enabled) is not bool:raise EvidenceError('Calendar flag must be boolean')
        self.calendar_enabled=enabled
        self.closed_dates=TEST_CLOSED_DATES if enabled else None

    def _epoch(self):
        return self.db.execute('SELECT epoch FROM policy_epoch WHERE singleton=1').fetchone()[0]

    def _reject(self, case, name, msg):
        self.db.execute('INSERT INTO legal_rejections(case_id,event_or_artifact,reason,policy_epoch,date) VALUES(?,?,?,?,?)',
                        (str(case),str(name),str(msg)[:250],self._epoch(),self.now))

    def _check_actor(self, env:dict,case:str,role:str,fields:set[str],schema:str):
        if case not in self.role_pubs or role not in self.role_pubs[case]:
            raise EvidenceError('Unknown case/actor role')
        b=verify(self.role_pubs[case][role],env,fields)
        if b['schema']!=schema or b['case']!=case or b['role']!=role or not b['nonce']:
            raise EvidenceError('Actor schema, case, role, or nonce mismatch')
        return b

    def record_event(self, envelope:dict) -> dict:
        try:
            if not isinstance(envelope,dict) or not isinstance(envelope.get('body'),dict):
                raise EvidenceError('Unsigned event')
            b=envelope['body'];case=b['case'];event=b['event'];role=b['role']
            if event not in EVENT_ROLES or EVENT_ROLES[event]!=role:
                raise EvidenceError('Event not authorized for claimed actor')
            b=self._check_actor(envelope,case,role,EVENT_FIELDS,'case-actor-event-v1')
            if type(b['sequence']) is not int or b['sequence']<1 or not b['event_id']:
                raise EvidenceError('Event sequence invalid')
            if event in {'producer_notice','self_discovery'}:
                if not isinstance(b['source_id'],str) or not self.db.execute(
                    'SELECT 1 FROM sources WHERE case_id=? AND source_id=?',(case,b['source_id'])).fetchone():
                    raise EvidenceError('Case/source not pinned')
            elif b['source_id'] is not None:
                raise EvidenceError('This event is case-level and has no source identifier')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                if self.db.execute('SELECT 1 FROM legal_events WHERE event_id=?',(b['event_id'],)).fetchone():
                    raise EvidenceError('Event ID already used')
                last=self.db.execute('SELECT MAX(sequence) FROM legal_events WHERE case_id=? AND actor_role=?',
                                     (case,role)).fetchone()[0]
                if last is not None and b['sequence']<=last:raise EvidenceError('Replayed/out-of-order actor event')
                if event=='return_or_destruction' and not self.db.execute(
                    'SELECT 1 FROM legal_events WHERE case_id=? AND event_name IN ("final_termination","producer_notice")',(case,)).fetchone():
                    raise EvidenceError('Cannot attest disposition without initiating event')
                if event=='written_confirmation' and not self.db.execute(
                    'SELECT 1 FROM legal_events WHERE case_id=? AND event_name="return_or_destruction"',(case,)).fetchone():
                    raise EvidenceError('No recorded return/destruction anchor')
                if event=='receipt_of_log_and_replacement' and not self.db.execute(
                    'SELECT 1 FROM legal_events WHERE case_id=? AND event_name="producer_notice"',(case,)).fetchone():
                    raise EvidenceError('No producer notice for log receipt')
                # Clock start for notice is locally accepted receipt, not producer-signed issued time.
                self.db.execute('UPDATE policy_epoch SET epoch=epoch+1 WHERE singleton=1')
                epoch=self._epoch()
                self.db.execute('INSERT INTO legal_events VALUES(?,?,?,?,?,?,?, ?, ?)',
                                (b['event_id'],case,event,b['source_id'],role,b['sequence'],self.now,epoch,stable_json(envelope)))
                if event in {'producer_notice','self_discovery'}:
                    self.db.execute('INSERT INTO notices VALUES(?,?,?,?,?,?)',
                                    (b['event_id'],case,b['source_id'],(self.db.execute('SELECT COALESCE(MAX(owner_sequence),0)+1 FROM notices WHERE case_id=?',(case,)).fetchone()[0]),epoch,stable_json(envelope)))
                self.db.execute('COMMIT')
                return {'status':'RECORDED','event':event,'case':case,'role':role,'epoch':epoch,'date':self.now}
            except BaseException:
                self.db.execute('ROLLBACK')
                raise
        except Exception as e:
            self._reject(envelope.get('body',{}).get('case','?') if isinstance(envelope,dict) else '?',
                         envelope.get('body',{}).get('event_id','?') if isinstance(envelope,dict) else '?',str(e))
            return {'status':'REJECTED','reason':str(e)[:250], 'epoch':self._epoch()}

    def _resolve_proof(self,bundle:dict,claimed:list[str]) -> tuple[dict,list[str],bytes]:
        if not isinstance(bundle,dict) or set(bundle)!={'schema','output_b64','legacy_seal','execution_attestation'}:
            raise EvidenceError('Stage Q proof bundle required')
        output=base64.b64decode(bundle['output_b64'],validate=True)
        if len(output)>65536:raise EvidenceError('Oversized effect')
        # EXACT unchanged Stage Q cryptographic code-binding validator.
        code=validate_v2(self.gate,bundle['legacy_seal'],bundle['execution_attestation'],output,
                         self.trust['launcher_sha256'],23322,23321)
        if code['program_sha256'] not in self.trust['approved_program_sha256']:
            raise EvidenceError('Unapproved program hash')
        program_path=next((p for p in (ROOT/'vendor_stage_q'/'programs').glob('*.py')
                          if digest(p.read_bytes())==code['program_sha256']),None)
        if program_path is None:raise EvidenceError('Approved program bytes unavailable')
        body=bundle['legacy_seal']['body']
        if body['case'] not in self.role_pubs or not body['closed']:raise EvidenceError('Unknown case / nonclosed evidence')
        resolved=set();events=body['events']
        if not events or len(events)>1000:raise EvidenceError('Missing/large events')
        for idx,e in enumerate(events,1):
            if set(e)!={'seq','type','id','source_sha256'} or type(e['seq']) is not int or e['seq']!=idx:
                raise EvidenceError('Malformed ordered observed event')
            if e['type']=='source':
                actual=self.db.execute('SELECT source_sha256 FROM sources WHERE case_id=? AND source_id=?',
                                       (body['case'],e['id'])).fetchone()
                if not actual or actual[0]!=e['source_sha256']:raise EvidenceError('Source unpinned or digest changed')
                resolved.add(e['id'])
            elif e['type']=='parent':
                if e['source_sha256'] is not None:raise EvidenceError('Parent digest invalid')
                parent=self.db.execute('SELECT case_id,resolved_sources FROM artifacts WHERE artifact_id=?',(e['id'],)).fetchone()
                if not parent or parent[0]!=body['case']:raise EvidenceError('Parent unavailable/cross-case')
                resolved.update(json.loads(parent[1]))
            else:raise EvidenceError('Unknown observed event type')
        exact=self.db.execute('SELECT source_id FROM sources WHERE case_id=? AND source_sha256=?',
                              (body['case'],body['output_sha256'])).fetchall()
        resolved.update(r[0] for r in exact)
        if sorted(set(claimed))!=sorted(resolved):raise EvidenceError('Declared read set differs from signed closure')
        if self.db.execute('SELECT 1 FROM artifacts WHERE artifact_id=? OR run_id=?',
                           (body['artifact_id'],body['run_id'])).fetchone():
            raise EvidenceError('Reused artifact or broker run')
        return body,sorted(resolved),output

    def attempt(self,bundle:dict,actor_envelope:dict,claimed:list[str],cached_approval=False) -> dict:
        raw=bundle.get('legacy_seal',{}).get('body',{}) if isinstance(bundle,dict) else {}
        case=str(raw.get('case','?'));aid=str(raw.get('artifact_id','?'))
        proof_hash=digest(stable_json({'bundle':bundle,'actor':actor_envelope,'claimed':claimed}).encode())
        self.db.execute('BEGIN IMMEDIATE')
        verdict='HOLD';why='';sources=[];role=None;out=b'';epoch=self._epoch();b=None
        try:
            try:
                if not isinstance(claimed,list) or not all(isinstance(x,str) for x in claimed):
                    raise EvidenceError('Claimed sources malformed')
                ab=actor_envelope.get('body',{})
                role=ab['role']; a=self._check_actor(actor_envelope,case,role,AUTH_FIELDS,'actor-effect-authorization-v1')
                if role not in {'receiving_party','receiving_counsel'}:
                    raise EvidenceError('Actor has no external write authority')
                if a['artifact_id']!=aid or a['action']!='EXTERNAL_EFFECT':
                    raise EvidenceError('Actor consent not bound to this artifact and action')
                if self.db.execute('SELECT 1 FROM legal_effect_attempts WHERE proof_sha256=?',(proof_hash,)).fetchone():
                    raise EvidenceError('Duplicate use of same authorization/proof')
                b,sources,out=self._resolve_proof(bundle,claimed)
                restricted={r[0] for r in self.db.execute(
                    'SELECT DISTINCT source_id FROM notices WHERE case_id=?',(case,))}
                affected=bool(restricted.intersection(sources))
                final=self.db.execute('SELECT 1 FROM legal_events WHERE case_id=? AND event_name="final_termination"',(case,)).fetchone() is not None
                protected=any(self.trust['source_classifications'][case].get(s)=='covered_final' for s in sources) # recipient-pinned synthetic facts
                current_event='C_PRIV_NOTICE' if restricted else 'NO_PRIVILEGED_INFORMATION'
                pd=self.gate.policy.decide(case=case,event=current_event,action='EXTERNAL_EFFECT',kind=b['kind'],
                         facts={'contains_specified':affected,'claim_active':bool(restricted)})
                if affected or pd.verdict=='BLOCK':
                    verdict='BLOCK';why='Observed source intersects recipient-recorded notice/self-discovery'
                elif final and protected:
                    verdict='BLOCK';why='Final disposition: source designated as covered by the synthetic fixture'
                else:
                    verdict=pd.verdict;why=pd.reason
                # A legal due date NEVER automatically makes restricted information safe.
                # Register all verified artifacts, even blocked, to prevent laundering via parent edges.
                self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)',
                                (aid,b['run_id'],case,b['kind'],b['output_sha256'],stable_json(sources),stable_json(bundle['legacy_seal'])))
            except (EvidenceError,KeyError,TypeError,ValueError,AttributeError) as e:
                verdict='HOLD';why=str(e)[:250];sources=[]
            applied=(verdict=='ALLOW_SCOPED')
            cur=self.db.execute('INSERT INTO legal_effect_attempts(case_id,artifact_id,role,verdict,persisted,policy_epoch,clock_date,sources,reason,proof_sha256,policy_digest,bundle_json,actor_envelope_json,declared_sources_json,client_cached_approval) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                (case,aid,role,verdict,int(applied),epoch,self.now,stable_json(sources),why,proof_hash,self.gate.policy.digest,stable_json(bundle),stable_json(actor_envelope),stable_json(claimed),int(bool(cached_approval))))
            if applied:
                self.db.execute('INSERT INTO legal_effects(attempt_id,case_id,artifact_id,payload_sha256,policy_epoch,clock_date) VALUES(?,?,?,?,?,?)',
                                (cur.lastrowid,case,aid,digest(out),epoch,self.now))
            self.db.execute('COMMIT')
            return {'verdict':verdict,'persisted':applied,'policy_epoch':epoch,'date':self.now,'role':role,
                    'sources':sources,'reason':why,'artifact_id':aid}
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def obligations(self,case:str, asof:str|None=None) -> list[dict]:
        date=asof or self.now;parsedate(date)
        evs=[{'id':r[0],'event':r[1],'date':r[2]} for r in self.db.execute(
            'SELECT event_id,event_name,received_date FROM legal_events WHERE case_id=? ORDER BY rowid',(case,))]
        out=[]
        for duty in self.duties:
            if duty.case!=case:continue
            anchors=[e for e in evs if e['event']==duty.event]
            if not anchors:continue
            start=anchors[0]['date']
            compname=counterpart_completion(duty)
            comps=[e for e in evs if e['event']==compname and e['date']>=start] if compname else []
            state=evaluate_due(start,duty.amount,duty.unit,date,comps[0]['date'] if comps else None,
                               closed_dates=self.closed_dates)
            out.append({'case':case,'clause':duty.clause,'actor':duty.actor,'action':duty.action,
                        'trigger':duty.event,'start':start,'amount':duty.amount,'unit':duty.unit,
                        'source_url':duty.source_url,**state})
        return out

    def archive(self,case:str,note_id:str,token:dict,qualified:bool,contains_specified:bool|None)->dict:
        # Archiving is a distinct restricted-storage action; never a privilege-use authorization.
        if type(qualified) is not bool or contains_specified is not None and type(contains_specified) is not bool:
            raise EvidenceError('Archive facts type invalid')
        ab=token.get('body',{}) if isinstance(token,dict) else {}
        try:
            b=self._check_actor(token,case,'receiving_counsel',AUTH_FIELDS,'actor-effect-authorization-v1')
            if b['action']!='ARCHIVE' or b['artifact_id']!=note_id:raise EvidenceError('Archive evidence unbound')
        except Exception as e:
            return {'verdict':'HOLD','persisted':False,'reason':str(e)[:200]}
        frozen=self.trust['archive_classifications'].get(case,{}).get(note_id)
        if frozen is None:
            return {'verdict':'HOLD','persisted':False,'reason':'Recipient has no verified archive classification'}
        if frozen['qualified'] is not qualified or frozen['contains_specified'] is not contains_specified:
            return {'verdict':'HOLD','persisted':False,'reason':'Caller archive facts conflict with recipient-owned evidence'}
        self.db.execute('BEGIN IMMEDIATE')
        try:
            noticed=self.db.execute('SELECT COUNT(*) FROM notices WHERE case_id=?',(case,)).fetchone()[0]>0
            final=self.db.execute('SELECT 1 FROM legal_events WHERE case_id=? AND event_name="final_termination"',(case,)).fetchone() is not None
            if not final or not qualified or contains_specified is None:
                verdict='HOLD'
            else:
                pd=self.gate.policy.decide(case=case,event='FINAL_TERMINATION',kind='legal_memo',action='ARCHIVE',
                    facts={'contains_specified':contains_specified,'claim_active':noticed,'counsel_record':True,
                           'qualified_archive':qualified,'is_covered_final_material':True})
                verdict=pd.verdict
            persisted=verdict=='ALLOW_RESTRICTED_STORAGE'
            if persisted:self.db.execute('INSERT INTO legal_archive(case_id,note_id,qualified_counsel_attested,policy_epoch,reuse_blocked,actor_envelope_json,trusted_facts_digest) VALUES(?,?,?,?,1,?,?)',
                                         (case,note_id,1,self._epoch(),stable_json(token),digest(stable_json(frozen).encode())))
            self.db.execute('COMMIT')
            return {'verdict':verdict,'persisted':persisted,'epoch':self._epoch()}
        except BaseException:self.db.execute('ROLLBACK');raise

    def challenge_copy(self,case:str,source_id:str,token:dict)->dict:
        """Restricts iOttie's exception to ONE recorded, non-reusable challenge copy.
        The physical source bytes remain in the protected vault; this DB only
        records a restricted retention permission, not deletion or actual copies.
        """
        ab=token.get('body',{}) if isinstance(token,dict) else {}
        try:
            b=self._check_actor(token,case,'receiving_challenger',AUTH_FIELDS,'actor-effect-authorization-v1')
            if b['action']!='CHALLENGE_COPY' or b['artifact_id']!=source_id:
                raise EvidenceError('Challenge copy authorization not bound to source/action')
        except Exception as exc:
            return {'verdict':'HOLD','persisted':False,'reason':str(exc)[:200]}
        self.db.execute('BEGIN IMMEDIATE')
        try:
            noticed=self.db.execute('SELECT 1 FROM notices WHERE case_id=? AND source_id=?',(case,source_id)).fetchone()
            pinned=self.db.execute('SELECT 1 FROM sources WHERE case_id=? AND source_id=?',(case,source_id)).fetchone()
            exists=self.db.execute('SELECT 1 FROM legal_challenge_copy WHERE case_id=? AND source_id=?',(case,source_id)).fetchone()
            receipt=self.db.execute('SELECT MIN(received_date) FROM legal_events WHERE case_id=? AND event_name="receipt_of_log_and_replacement"',(case,)).fetchone()[0]
            challenge_deadline=deadline(receipt,7,'business_days',closed_dates=self.closed_dates) if receipt else None
            filed=self.db.execute('SELECT MIN(received_date) FROM legal_events WHERE case_id=? AND event_name="challenge_filed"',(case,)).fetchone()[0]
            expired=bool(receipt and (challenge_deadline is None or (self.now>challenge_deadline and not (filed and filed<=challenge_deadline))))
            if case!='iottie' or not noticed or not pinned or exists or expired:
                status='HOLD';reason='Not an eligible, timely single-copy iOttie privilege challenge'
            else:
                pd=self.gate.policy.decide(case=case,event='PRIVILEGE_CHALLENGE',action='PRIVILEGE_CHALLENGE',
                    kind='source_copy',facts={'contains_specified':True,'explicit_challenge_authorization':True},
                    proof={'court_challenge_only':True})
                status=pd.verdict;reason=pd.reason
                if status=='ALLOW_CHALLENGE_ONLY':
                    self.db.execute('INSERT INTO legal_challenge_copy(case_id,source_id,challenge_role,reserved_epoch,reserved_date,restriction,actor_envelope_json) VALUES(?,?,?,?,?,?,?)',
                        (case,source_id,'receiving_challenger',self._epoch(),self.now,'COURT_CHALLENGE_ONLY_NO_EXTERNAL_USE',stable_json(token)))
            self.db.execute('COMMIT')
            return {'verdict':status,'persisted':status=='ALLOW_CHALLENGE_ONLY','reason':reason,'epoch':self._epoch()}
        except BaseException:self.db.execute('ROLLBACK');raise

    def close(self):self.gate.close()
