"""Independent HTTP legal-source gateway, recording and signing actual tool reads."""
import argparse,json,sqlite3
from http.server import HTTPServer,BaseHTTPRequestHandler
from common import canon,signed,keypair,dbopen
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from urllib.parse import urlsplit,parse_qs

class Source(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  parsed=urlsplit(self.path)
  if parsed.path=='/ping':return self.response({'ok':True})
  if parsed.path!='/read':return self.response({'error':'unknown'},404)
  q=parse_qs(parsed.query);case=q.get('case',[''])[0];sid=q.get('source',[''])[0];run=q.get('run',[''])[0]
  db=self.server.db
  source=db.execute('SELECT body,source_type FROM sources WHERE case_id=? AND source_id=?',(case,sid)).fetchone()
  if not source:return self.response({'error':'unknown_source'},404)
  body,type_=source
  row=db.execute('INSERT INTO reads(run_id,case_id,source_id,source_type) VALUES(?,?,?,?) RETURNING id',(run,case,sid,type_)).fetchone()
  claim={'schema':'actual-tool-read-v1','read_id':row[0],'run_id':run,'case_id':case,'source_id':sid,'source_type':type_,'content_sha256':__import__('hashlib').sha256(body.encode()).hexdigest()}
  return self.response({'text':body,'receipt':signed(self.server.private,claim)})
 def response(self,obj,code=200):
  raw=canon(obj);self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,required=True);p.add_argument('--db',required=True);p.add_argument('--key',required=True);p.add_argument('--input',required=True);args=p.parse_args()
 key=Ed25519PrivateKey.from_private_bytes(bytes.fromhex(open(args.key).read().strip()))
 docs=json.load(open(args.input));db=dbopen(args.db)
 db.executescript('CREATE TABLE IF NOT EXISTS sources(case_id TEXT,source_id TEXT,body TEXT,source_type TEXT,PRIMARY KEY(case_id,source_id)); CREATE TABLE IF NOT EXISTS reads(id INTEGER PRIMARY KEY,run_id TEXT,case_id TEXT,source_id TEXT,source_type TEXT);')
 for row in docs['sources']:db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?)',(row['case_id'],row['source_id'],row['text'],row['source_type']))
 srv=HTTPServer(('127.0.0.1',args.port),Source);srv.db=db;srv.private=key
 try:srv.serve_forever()
 finally:srv.server_close();db.close()
if __name__=='__main__':main()
