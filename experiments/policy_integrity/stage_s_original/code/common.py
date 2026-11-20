import base64,hashlib,json,os,sqlite3
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def keypair():
 k=Ed25519PrivateKey.generate()
 return k,base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
def signed(k,obj):return {'body':obj,'signature':base64.b64encode(k.sign(canon(obj))).decode()}
def verify(pk,env):
 try:
  Ed25519PublicKey.from_public_bytes(base64.b64decode(pk)).verify(base64.b64decode(env['signature']),canon(env['body']));return True
 except Exception:return False

def post(url,obj):
 import urllib.request
 data=canon(obj)
 try:
  with urllib.request.urlopen(urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'}),timeout=10) as r:return json.loads(r.read())
 except urllib.error.HTTPError as exc:
  raise RuntimeError(f"HTTP {exc.code}: {exc.read()[:500]!r}") from exc
def get(url):
 import urllib.request
 with urllib.request.urlopen(url,timeout=10) as r:return json.loads(r.read())
def dbopen(path):
 db=sqlite3.connect(path,isolation_level=None,timeout=10)
 db.execute('PRAGMA journal_mode=DELETE')
 return db
