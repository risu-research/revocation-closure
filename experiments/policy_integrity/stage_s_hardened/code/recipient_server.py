"""Independent HTTP recipient with atomic SQLite policy check at write time.
Its decisions do NOT use the agent's claimed legal-clock values; actor events set local epochs.
"""
import argparse,json,base64,os
from a0_entry import A0Gate
from http.server import HTTPServer,BaseHTTPRequestHandler
from common import canon,sha,verify,dbopen

class Recipient(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def response(self,obj,code=200):
  b=canon(obj);self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if self.path=='/ping':return self.response({'ok':True})
  return self.response({'error':'unknown'},404)
 def do_POST(self):
  try:
   length=int(self.headers.get('Content-Length','0'));obj=json.loads(self.rfile.read(length))
   if self.path=='/notice':out=self.notice(obj)
   elif self.path=='/write':out=self.write(obj)
   else:return self.response({'error':'unknown'},404)
   return self.response(out)
  except Exception as e:
   return self.response({'error':type(e).__name__+': '+str(e)},500)
 def notice(self,obj):
  event=obj['event'];body=event.get('body',{})
  case=body.get('case');source=body.get('source')
  producer_notice=(body.get('event')=='privilege_notice' and body.get('role')=='producer' and verify(self.server.trust['producer_pub'],event))
  receiver_discovery=(body.get('case')=='napoli' and body.get('event')=='self_discovery' and body.get('role')=='receiving_party' and verify(self.server.trust['receiving_pub'],event))
  if not (producer_notice or receiver_discovery):
   return {'accepted':False,'reason':'invalid_role_or_event_authority'}
  db=self.server.db
  try:
   db.execute('BEGIN IMMEDIATE')
   db.execute('INSERT INTO events(case_id,source_id,event_id,envelope) VALUES(?,?,?,?)',(case,source,body['event_id'],json.dumps(event)))
   db.execute('INSERT INTO policy(case_id,source_id,epoch,revoked) VALUES(?,?,1,1) ON CONFLICT(case_id,source_id) DO UPDATE SET epoch=epoch+1,revoked=1',(case,source))
   db.execute('COMMIT');return {'accepted':True}
  except Exception as e:
   db.execute('ROLLBACK');return {'accepted':False,'reason':type(e).__name__}
 def write(self,obj):
  db=self.server.db;mode=obj['mode'];permit=obj['permit'];data=obj['artifact'];read_receipts=obj['read_receipts'];owner=obj.get('owner_envelope')
  trace=json.dumps(read_receipts,sort_keys=True)
  sources=[];valid_receipts=True
  for r in read_receipts:
   ok=verify(self.server.trust['source_pub'],r)
   valid_receipts &= ok
   if ok:sources.append(r['body']['source_id'])
  valid=verify(self.server.trust['issuer_pub'],permit)
  p=permit.get('body',{});digest=sha(data['content'])
  valid=valid and p.get('case')==data['case'] and p.get('audience')=='INDEPENDENT_RECIPIENT' and p.get('artifact_sha256')==digest and p.get('source_ids')==sorted(set(sources)) and p.get('action')=='STORE_DOCUMENT' and p.get('target')=='legal-effects'
  valid=valid and all(r.get('body',{}).get('case_id')==data['case'] and r.get('body',{}).get('run_id')==data['run_id'] for r in read_receipts)
  # The policy protects any derived artifact that has a signed read of revoked synthetic evidence.
  valid=valid and valid_receipts and bool(read_receipts)
  # Epoch checks are performed *inside* the write transaction below.
  if mode=='owner_live':valid=valid and owner is not None and verify(self.server.trust['owner_pub'],owner) and owner['body'].get('permit_id')==p.get('permit_id') and owner['body'].get('action')=='STORE_DOCUMENT'
  db.execute('BEGIN IMMEDIATE')
  try:
   logical_epoch=db.execute('SELECT COALESCE(MAX(epoch),0) FROM policy WHERE case_id=?',(data['case'],)).fetchone()[0]
   valid=valid and isinstance(p.get('expiry_epoch'),int) and p['expiry_epoch']>logical_epoch
   revoked=[]
   for sid in set(sources):
    row=db.execute('SELECT revoked FROM policy WHERE case_id=? AND source_id=?',(data['case'],sid)).fetchone()
    if row and row[0]:revoked.append(sid)
   policy_check=(mode in ('live','owner_live'))
   # The trusted A0 IR is checked at the same BEGIN IMMEDIATE write boundary.
   # A static/cached approval never overrides recipient-acknowledged revocation.
   a0_verdict=self.server.a0.decide(data['case'],read_receipts,revoked,mode) if valid else None
   if not valid:verdict='HOLD_INVALID_EVIDENCE'
   elif a0_verdict is not None:verdict=a0_verdict
   elif policy_check and revoked:verdict='BLOCK_REVOKED'
   elif db.execute('SELECT COUNT(*) FROM effects WHERE permit_id=?',(p.get('permit_id'),)).fetchone()[0]>0:verdict='BLOCK_DUPLICATE'
   else:verdict='ALLOW'
   if verdict=='ALLOW':
    db.execute('INSERT INTO effects(case_id,run_id,permit_id,mode,content,content_sha256,sources) VALUES(?,?,?,?,?,?,?)',(data['case'],data['run_id'],p['permit_id'],mode,data['content'],digest,json.dumps(sorted(set(sources)))))
   cur=db.execute('INSERT INTO attempts(case_id,run_id,mode,permit_id,decision,revoked_sources,observed_sources,permit_valid,content_sha256) VALUES(?,?,?,?,?,?,?,?,?) RETURNING id',
     (data['case'],data['run_id'],mode,p.get('permit_id'),verdict,json.dumps(sorted(revoked)),json.dumps(sorted(set(sources))),int(valid),digest))
   attempt_id=cur.fetchone()[0]
   db.execute('COMMIT');return {'decision':verdict,'persisted':verdict=='ALLOW','attempt_id':attempt_id,'revoked_sources':sorted(revoked)}
  except Exception:
   db.execute('ROLLBACK');raise

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,required=True);p.add_argument('--db',required=True);p.add_argument('--trust',required=True);args=p.parse_args()
 db=dbopen(args.db);db.executescript('''
 CREATE TABLE IF NOT EXISTS policy(case_id TEXT,source_id TEXT,epoch INTEGER NOT NULL,revoked INTEGER NOT NULL,PRIMARY KEY(case_id,source_id));
 CREATE TABLE IF NOT EXISTS events(case_id TEXT,source_id TEXT,event_id TEXT UNIQUE,envelope TEXT);
 CREATE TABLE IF NOT EXISTS effects(id INTEGER PRIMARY KEY,case_id TEXT,run_id TEXT,permit_id TEXT,mode TEXT,content TEXT,content_sha256 TEXT,sources TEXT);
 CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,case_id TEXT,run_id TEXT,mode TEXT,permit_id TEXT,decision TEXT,revoked_sources TEXT,observed_sources TEXT,permit_valid INTEGER,content_sha256 TEXT);''')
 srv=HTTPServer(('127.0.0.1',args.port),Recipient);srv.db=db;srv.trust=json.load(open(args.trust));srv.a0=A0Gate(os.environ.get("A0_POLICY_PATH"))
 try:srv.serve_forever()
 finally:srv.server_close();db.close()
if __name__=='__main__':main()
