#!/usr/bin/env python3
"""Independent HTTP/SQLite receiver for fixed synthetic effect fixtures.
Uses source-only lexical proposals. Gold and scenario oracle are not imported here.
No claim of production-grade auth or legal correctness.
"""
import argparse,hashlib,hmac,json,sqlite3,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def dig(v):return hashlib.sha256(v.encode()).hexdigest()
def signature(key,v):return hmac.new(key,canonical(v),hashlib.sha256).hexdigest()

def policy_decide(p, case, source, effect, actor, delivered_event, view):
    if source=='clean':return 'ALLOW','independent_clean'
    if source!='protected':return 'HOLD','unknown_source'
    if view=='static':return 'ALLOW','cached_token_only'
    if delivered_event is None:return 'ALLOW','no_recipient_notice_received'
    proposals=[x for x in p if x['case_id']==case]
    actions={x['action'] for x in proposals if x['action']!='unknown'}
    restrictive=bool(actions.intersection({'return_claimed_material','return_confidential_material',
         'return_or_destroy_protected_material','destroy_copies_and_derivatives',
         'stop_examination_disclosure','suspend_use','notify_producer_counsel','sealed_retention_no_use'}))
    if effect=='restricted_archive':
        if actor=='counsel' and 'restricted_archival_retention' in actions:return 'ALLOW','limited_archive'
        return 'HOLD','archive_exception_unverified'
    if effect=='sealed_challenge_retention':
        if 'sealed_retention_no_use' in actions:return 'ALLOW','sequestered_restricted_retention'
        return 'HOLD','challenge_exception_unverified'
    if effect in ('external_write','external_write_with_old_token','ordinary_redisclosure'):
        return ('BLOCK','recipient_live_restriction') if restrictive else ('HOLD','operative_restriction_unresolved')
    return 'HOLD','unsupported_effect_type'

class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,obj,code=200):
    b=canonical(obj);self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
    return self.send({'alive':True}) if self.path=='/ping' else self.send({'error':'404'},404)
 def do_POST(self):
    try:
      n=int(self.headers.get('Content-Length','0'));assert 0<n<200000
      obj=json.loads(self.rfile.read(n))
      if obj.get('owner_auth')!=self.server.owner_auth:return self.send({'error':'unauthorized'},403)
      if self.path=='/issue':out=self.issue(obj)
      elif self.path=='/notice':out=self.notice(obj)
      elif self.path=='/write':out=self.write(obj)
      else:return self.send({'error':'404'},404)
      return self.send(out)
    except Exception as e:return self.send({'error':type(e).__name__+': '+str(e)},500)
 def issue(self,o):
    b=o['token_body'];db=self.server.db
    db.execute('BEGIN IMMEDIATE')
    try:
      ep=db.execute('SELECT COUNT(*) FROM notices WHERE scenario_id=?',(b['scenario_id'],)).fetchone()[0]
      bb={**b,'issue_epoch':ep};sig=signature(self.server.token_secret,bb)
      db.execute('INSERT INTO permits(permit_id,case_id,body,signature,issue_epoch) VALUES(?,?,?,?,?)',(b['permit_id'],b['case_id'],canonical(bb).decode(),sig,ep))
      db.execute('COMMIT');return {'body':bb,'signature':sig}
    except:db.execute('ROLLBACK');raise
 def notice(self,o):
    case,event=o['case_id'],o['event'];scenario=o['scenario_id'];db=self.server.db
    db.execute('BEGIN IMMEDIATE')
    try:
      db.execute('INSERT INTO notices(scenario_id,case_id,event) VALUES(?,?,?)',(scenario,case,event));db.execute('COMMIT');return {'received':True}
    except:db.execute('ROLLBACK');raise
 def write(self,o):
    db=self.server.db;tok=o['permit'];body=tok['body'];mode=o['mode'];txt=o['content']
    db.execute('BEGIN IMMEDIATE')
    try:
      row=db.execute('SELECT body,signature FROM permits WHERE permit_id=?',(body['permit_id'],)).fetchone()
      good=bool(row) and signature(self.server.token_secret,body)==tok['signature']
      good=good and row==(canonical(body).decode(),tok['signature']) and dig(txt)==body['content_sha256']
      good=good and body['case_id']==o['case_id'] and body['actor']==o['actor'] and body['effect']==o['effect']
      good=good and o['source_kind']==body['source_kind'] and body['scenario_id']==o['scenario_id']
      evs=[x[0] for x in db.execute('SELECT event FROM notices WHERE scenario_id=? ORDER BY id',(body['scenario_id'],))]
      event=evs[-1] if evs else None
      if not good:decision,why='HOLD','bad_signed_capability'
      else:decision,why=policy_decide(self.server.proposals,body['case_id'],body['source_kind'],body['effect'],body['actor'],event,mode)
      if decision=='ALLOW':db.execute('INSERT INTO effects(scenario_id,case_id,mode,content,content_sha256,permit_id) VALUES(?,?,?,?,?,?)',(body['scenario_id'],body['case_id'],mode,txt,dig(txt),body['permit_id']))
      db.execute('INSERT INTO attempts(scenario_id,case_id,mode,permit_id,decision,reason,visible_event,source_kind,requested_effect,actor,content_sha256,content) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(body['scenario_id'],body['case_id'],mode,body['permit_id'],decision,why,event,body['source_kind'],body['effect'],body['actor'],dig(txt),txt))
      db.execute('COMMIT');return {'decision':decision,'reason':why,'persisted':decision=='ALLOW'}
    except:db.execute('ROLLBACK');raise

def main():
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--keyfile',required=True);p.add_argument('--proposals',required=True);a=p.parse_args()
 db=sqlite3.connect(a.db,isolation_level=None,check_same_thread=False)
 db.executescript('''PRAGMA journal_mode=WAL;
 CREATE TABLE IF NOT EXISTS permits(permit_id TEXT PRIMARY KEY,case_id TEXT,body TEXT,signature TEXT,issue_epoch INTEGER);
 CREATE TABLE IF NOT EXISTS notices(id INTEGER PRIMARY KEY AUTOINCREMENT,scenario_id TEXT,case_id TEXT,event TEXT);
 CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,scenario_id TEXT UNIQUE,case_id TEXT,mode TEXT,permit_id TEXT,decision TEXT,reason TEXT,visible_event TEXT,source_kind TEXT,requested_effect TEXT,actor TEXT,content_sha256 TEXT,content TEXT);
 CREATE TABLE IF NOT EXISTS effects(id INTEGER PRIMARY KEY AUTOINCREMENT,scenario_id TEXT UNIQUE,case_id TEXT,mode TEXT,content TEXT,content_sha256 TEXT,permit_id TEXT);''')
 keys=json.loads(Path(a.keyfile).read_text())
 server=ThreadingHTTPServer(('127.0.0.1',a.port),H);server.db=db;server.token_secret=bytes.fromhex(keys['token_secret']);server.owner_auth=keys['owner_auth'];server.proposals=json.loads(Path(a.proposals).read_text())['proposals']
 try:server.serve_forever()
 finally:server.server_close();db.close()
if __name__=='__main__':main()
