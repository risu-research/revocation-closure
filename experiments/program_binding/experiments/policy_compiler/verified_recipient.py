"""Recipient-verified synthetic effect boundary, Stage O.

Authenticated owner notices; broker-signed complete observed-read manifests; observed
parent edges and transitive dependency closure; exact output-byte binding; atomic
current-policy checks. This does NOT prove that an instrumented read boundary was
exclusive. The broker and owner signing keys must live outside the untrusted agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from .policy_engine import CASES, KINDS, load_default, stable_json


class EvidenceError(ValueError):
    pass


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def sign(private: Ed25519PrivateKey, body: dict) -> dict:
    return {'body': body, 'signature': private.sign(stable_json(body).encode('utf-8')).hex()}


def verify(public: Ed25519PublicKey, token: dict, allowed_fields: set[str]) -> dict:
    if not isinstance(token, dict) or set(token) != {'body', 'signature'}:
        raise EvidenceError('Malformed signed envelope')
    body = token['body']
    if not isinstance(body, dict) or set(body) != allowed_fields:
        raise EvidenceError('Unexpected signed fields')
    try:
        public.verify(bytes.fromhex(token['signature']), stable_json(body).encode('utf-8'))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise EvidenceError('Signature invalid') from exc
    return body


class TrustedReadBroker:
    """Trusted process analogue; only broker-mediated source/parent reads are observed.

    The caller cannot author its own signed read-set, but this mock has no OS-level
    read isolation. `closed` certifies only the broker's own recorded observations.
    """
    def __init__(self, private_key: Ed25519PrivateKey):
        self._private_key = private_key
        self._runs: dict[str, dict] = {}

    def open_run(self, run_id: str, artifact_id: str, case: str, kind: str):
        if not run_id or not artifact_id or case not in CASES or kind not in KINDS or run_id in self._runs:
            raise EvidenceError('Invalid or duplicated broker run')
        self._runs[run_id] = {'case': case, 'kind': kind, 'artifact_id': artifact_id,
                              'events': [], 'sealed': False}

    def observe_source(self, run_id: str, source_id: str, source_bytes: bytes):
        r = self._active(run_id)
        r['events'].append({'seq': len(r['events']) + 1, 'type': 'source',
                            'id': source_id, 'source_sha256': digest(source_bytes)})

    def observe_parent(self, run_id: str, parent_artifact_id: str):
        r = self._active(run_id)
        r['events'].append({'seq': len(r['events']) + 1, 'type': 'parent',
                            'id': parent_artifact_id, 'source_sha256': None})

    def _active(self, run_id: str):
        r = self._runs.get(run_id)
        if not r or r['sealed']:
            raise EvidenceError('Run missing or sealed')
        return r

    def seal(self, run_id: str, output: bytes, complete: bool = True) -> dict:
        r = self._active(run_id)
        if type(complete) is not bool:
            raise EvidenceError('Invalid completeness flag')
        r['sealed'] = True
        body = {'schema': 'broker-observed-reads-v1', 'run_id': run_id,
                'artifact_id': r['artifact_id'], 'case': r['case'], 'kind': r['kind'],
                'output_sha256': digest(output), 'closed': complete,
                'events': list(r['events'])}
        return sign(self._private_key, body)


def sign_notice(owner_key: Ed25519PrivateKey, notice_id: str, case: str,
                source_id: str, sequence: int) -> dict:
    return sign(owner_key, {'schema': 'owner-privilege-notice-v1',
                            'notice_id': notice_id, 'case': case,
                            'source_id': source_id, 'sequence': sequence,
                            'event': 'C_PRIV_NOTICE'})


@dataclass(frozen=True)
class RecipientDecision:
    status: str
    persisted: bool
    reason: str
    policy_epoch: int
    evidence_status: str
    resolved_sources: tuple[str, ...]
    declared_sources: tuple[str, ...]
    policy_verdict: str


class VerifiedRecipient:
    """Recipient owns source/owner/broker trust anchors and its effect store.

    Only `accept_owner_notice` and `attempt_effect` are exposed to outside callers.
    All `pin_*` methods are trusted setup, NEVER public HTTP routes. Each decision
    rechecks evidence, source-to-claim status, and actual write in BEGIN IMMEDIATE.
    """
    SEAL_FIELDS = {'schema','run_id','artifact_id','case','kind','output_sha256','closed','events'}
    NOTICE_FIELDS = {'schema','notice_id','case','source_id','sequence','event'}

    def __init__(self, db_path: Path, broker_pub: Ed25519PublicKey,
                 owner_pubs: dict[str, Ed25519PublicKey]):
        self.db_path = Path(db_path)
        self.policy = load_default()
        self.broker_pub = broker_pub
        self.owner_pubs = owner_pubs.copy()
        self.db = sqlite3.connect(str(db_path), isolation_level=None, timeout=15)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=15000')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS sources (
          case_id TEXT NOT NULL, source_id TEXT NOT NULL, source_sha256 TEXT NOT NULL,
          PRIMARY KEY(case_id,source_id));
        CREATE TABLE IF NOT EXISTS notices (
          notice_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, source_id TEXT NOT NULL,
          owner_sequence INTEGER NOT NULL, epoch INTEGER NOT NULL, signed_envelope TEXT NOT NULL,
          UNIQUE(case_id,owner_sequence),
          FOREIGN KEY(case_id,source_id) REFERENCES sources(case_id,source_id));
        CREATE TABLE IF NOT EXISTS policy_epoch (singleton INTEGER PRIMARY KEY CHECK(singleton=1), epoch INTEGER NOT NULL);
        INSERT OR IGNORE INTO policy_epoch VALUES(1,0);
        CREATE TABLE IF NOT EXISTS artifacts (
          artifact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL UNIQUE,
          case_id TEXT NOT NULL, kind TEXT NOT NULL, output_sha256 TEXT NOT NULL,
          resolved_sources TEXT NOT NULL, broker_seal TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts (
          attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, artifact_id TEXT, run_id TEXT,
          action TEXT, verdict TEXT NOT NULL, persisted INTEGER NOT NULL,
          evidence_status TEXT NOT NULL, reason TEXT NOT NULL, policy_epoch INTEGER NOT NULL,
          policy_digest TEXT NOT NULL, policy_verdict TEXT NOT NULL, resolved_sources TEXT NOT NULL,
          declared_sources TEXT NOT NULL, client_cached_approval INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS effects (
          effect_id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER UNIQUE NOT NULL,
          artifact_id TEXT NOT NULL, synthetic_payload TEXT NOT NULL,
          policy_epoch INTEGER NOT NULL, policy_digest TEXT NOT NULL, output_sha256 TEXT NOT NULL,
          FOREIGN KEY(attempt_id) REFERENCES attempts(attempt_id));
        ''')

    def close(self):
        self.db.close()

    def pin_source(self, case: str, source_id: str, source_bytes: bytes):
        """Trusted one-time registry. In production ingest via authenticated custody."""
        if case not in CASES or not source_id or not isinstance(source_bytes, bytes):
            raise EvidenceError('Invalid pinned source')
        h = digest(source_bytes)
        row = self.db.execute('SELECT source_sha256 FROM sources WHERE case_id=? AND source_id=?',
                              (case,source_id)).fetchone()
        if row and row[0] != h:
            raise EvidenceError('Source digest cannot change')
        self.db.execute('INSERT OR IGNORE INTO sources VALUES (?,?,?)', (case,source_id,h))

    def accept_owner_notice(self, envelope: dict) -> int:
        """Authenticates notice issuer and source identity, not merits of privilege."""
        if not isinstance(envelope, dict) or not isinstance(envelope.get('body'), dict):
            raise EvidenceError('Malformed notice')
        case = envelope['body'].get('case')
        owner = self.owner_pubs.get(case)
        if owner is None:
            raise EvidenceError('Unknown owner for this case')
        b = verify(owner, envelope, self.NOTICE_FIELDS)
        if b['schema'] != 'owner-privilege-notice-v1' or b['event'] != 'C_PRIV_NOTICE':
            raise EvidenceError('Wrong notice schema/event')
        if (not isinstance(b['sequence'], int) or isinstance(b['sequence'], bool)
                or b['sequence'] < 1 or not b['notice_id']):
            raise EvidenceError('Invalid owner sequence')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.db.execute('SELECT 1 FROM sources WHERE case_id=? AND source_id=?',
                               (case,b['source_id'])).fetchone() is None:
                raise EvidenceError('Notice references unregistered source')
            last = self.db.execute('SELECT MAX(owner_sequence) FROM notices WHERE case_id=?', (case,)).fetchone()[0]
            if last is not None and b['sequence'] <= last:
                raise EvidenceError('Replay or out-of-order owner sequence')
            self.db.execute('UPDATE policy_epoch SET epoch=epoch+1 WHERE singleton=1')
            epoch = self.db.execute('SELECT epoch FROM policy_epoch WHERE singleton=1').fetchone()[0]
            self.db.execute('INSERT INTO notices VALUES(?,?,?,?,?,?)',
                            (b['notice_id'],case,b['source_id'],b['sequence'],epoch,stable_json(envelope)))
            self.db.execute('COMMIT')
            return epoch
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def attempt_effect(self, seal: dict, output: bytes, claimed_sources: list[str],
                       action: str = 'EXTERNAL_EFFECT', cached_approval: bool = False) -> RecipientDecision:
        """Client-controlled flags NEVER authorize effect. Proof+policy and write atomic."""
        if action not in {'USE','SHARE','EXTERNAL_EFFECT'}:
            raise EvidenceError('Only non-destructive effects supported')
        if not isinstance(output, bytes) or not isinstance(claimed_sources, list):
            raise EvidenceError('Output must be bytes and claimed source list')
        if any(not isinstance(s,str) for s in claimed_sources):
            raise EvidenceError('Malformed client source list')
        if not isinstance(seal,dict) or not isinstance(seal.get('body'),dict):
            raise EvidenceError('Malformed seal')
        # These identifiers are untrusted until verified; we store for audit only.
        unsigned = seal['body']
        artifact_id = str(unsigned.get('artifact_id', 'UNKNOWN'))[:160]
        run_id = str(unsigned.get('run_id', 'UNKNOWN'))[:160]
        declared = tuple(sorted(set(claimed_sources)))
        self.db.execute('BEGIN IMMEDIATE')
        try:
            epoch = self.db.execute('SELECT epoch FROM policy_epoch WHERE singleton=1').fetchone()[0]
            status, reason, evidence_status, policy_verdict = 'HOLD','', 'INVALID','NOT_EVALUATED'
            resolved: tuple[str,...] = ()
            body: dict | None = None
            try:
                body = verify(self.broker_pub, seal, self.SEAL_FIELDS)
                if body['schema'] != 'broker-observed-reads-v1' or body['case'] not in CASES or body['kind'] not in KINDS:
                    raise EvidenceError('Unknown broker schema / object kind')
                if not body['artifact_id'] or not body['run_id']:
                    raise EvidenceError('Missing artifact/run identity')
                if not body['closed'] or type(body['closed']) is not bool:
                    raise EvidenceError('Read set is not closed by broker')
                if body['output_sha256'] != digest(output):
                    raise EvidenceError('Artifact bytes disagree with broker signed digest')
                if self.db.execute('SELECT 1 FROM artifacts WHERE artifact_id=? OR run_id=?',
                                   (body['artifact_id'],body['run_id'])).fetchone():
                    raise EvidenceError('Replayed artifact or reused broker run')
                seen_source=set();seen_parents=set()
                events=body['events']
                if not isinstance(events,list) or len(events)>1000:
                    raise EvidenceError('Malformed/excessive read events')
                for i,e in enumerate(events,1):
                    if not isinstance(e,dict) or set(e)!={'seq','type','id','source_sha256'}:
                        raise EvidenceError('Malformed signed read event')
                    if type(e['seq']) is not int or e['seq']!=i or e['type'] not in {'source','parent'} or not isinstance(e['id'],str):
                        raise EvidenceError('Noncontiguous or invalid read event')
                    if e['type']=='source':
                        actual=self.db.execute('SELECT source_sha256 FROM sources WHERE case_id=? AND source_id=?',
                                               (body['case'],e['id'])).fetchone()
                        if not actual or not isinstance(e['source_sha256'],str) or actual[0]!=e['source_sha256']:
                            raise EvidenceError('Unpinned or altered observed source')
                        seen_source.add(e['id'])
                    else:
                        if e['source_sha256'] is not None:
                            raise EvidenceError('Parent event uses source digest')
                        parent=self.db.execute('SELECT case_id,resolved_sources FROM artifacts WHERE artifact_id=?',
                                               (e['id'],)).fetchone()
                        if not parent or parent[0]!=body['case']:
                            raise EvidenceError('Parent artifact missing or cross-case')
                        seen_parents.add(e['id'])
                        seen_source.update(json.loads(parent[1]))
                # Independent byte-identity check: a complete output matching
                # a pinned source digest inherits that source for conservative
                # enforcement, even if no broker read was observed. This proves
                # byte equality, NOT that the source was causally read.
                exact_sources={r[0] for r in self.db.execute(
                    'SELECT source_id FROM sources WHERE case_id=? AND source_sha256=?',
                    (body['case'], body['output_sha256']))}
                seen_source.update(exact_sources)
                resolved=tuple(sorted(seen_source))
                evidence_status = ('BROKER_VERIFIED_AND_EXACT_CONTENT' if exact_sources
                                   else 'BROKER_VERIFIED')
                noticed={r[0] for r in self.db.execute('SELECT DISTINCT source_id FROM notices WHERE case_id=?',
                                                       (body['case'],))}
                affected=bool(noticed.intersection(seen_source))
                claim_active=bool(noticed)
                event='C_PRIV_NOTICE' if claim_active else 'NO_PRIVILEGED_INFORMATION'
                decision=self.policy.decide(case=body['case'],event=event,kind=body['kind'],action=action,
                                            facts={'contains_specified':affected,'claim_active':claim_active})
                policy_verdict=decision.verdict
                if affected:
                    status='BLOCK'
                    reason=('Pinned source has identical output bytes and a current notice'
                            if exact_sources.intersection(noticed)
                            else 'Observed source/parent dependency intersects authenticated current notice')
                elif declared != resolved:
                    status='HOLD'
                    evidence_status='CLIENT_PROVENANCE_CONFLICT'
                    reason='Client-declared source list differs from independently observed dependency closure'
                else:
                    status=decision.verdict
                    reason=decision.reason
                # Authenticated/sealed artifact is registered even when blocked, so
                # a later child cannot launder this parent into a clean artifact.
                self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)',
                                (body['artifact_id'],body['run_id'],body['case'],body['kind'],
                                 body['output_sha256'],stable_json(resolved),stable_json(seal)))
            except (EvidenceError, KeyError, TypeError, ValueError) as exc:
                status='HOLD'
                evidence_status='INVALID_OR_INCOMPLETE'
                reason=str(exc)[:500]
                policy_verdict='NOT_EVALUATED'
                # An invalid proof never registers its artifact or parent edges.
                resolved=()
            applied=status=='ALLOW_SCOPED'
            cur=self.db.execute('''INSERT INTO attempts(artifact_id,run_id,action,verdict,persisted,
                evidence_status,reason,policy_epoch,policy_digest,policy_verdict,resolved_sources,
                declared_sources,client_cached_approval) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (artifact_id,run_id,action,status,int(applied),evidence_status,reason,epoch,
                 self.policy.digest,policy_verdict,stable_json(resolved),stable_json(declared),int(bool(cached_approval))))
            if applied:
                self.db.execute('''INSERT INTO effects(attempt_id,artifact_id,synthetic_payload,policy_epoch,policy_digest,output_sha256)
                    VALUES(?,?,?,?,?,?)''',(cur.lastrowid,body['artifact_id'],'SYNTHETIC_EFFECT',epoch,self.policy.digest,digest(output)))
            self.db.execute('COMMIT')
            return RecipientDecision(status,applied,reason,epoch,evidence_status,resolved,declared,policy_verdict)
        except Exception:
            self.db.execute('ROLLBACK')
            raise
