"""Alter both a persisted SQL document and its local digest; offline auditor must fail."""
from __future__ import annotations
import json, shutil, sqlite3, hashlib, pathlib, subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
source=ROOT/'results/a0_enforced_primary'
dest=ROOT/'results/a0_tampered_copy'
if dest.exists():shutil.rmtree(dest)
shutil.copytree(source,dest)
db=dest/'camm_recipient.sqlite'
c=sqlite3.connect(db)
row=c.execute('select id,content from effects order by id limit 1').fetchone()
assert row, 'Expected saved control'
new_body=row[1]+' ALTERED_AT_REST_AFTER_SIGNATURE'
new_hash=hashlib.sha256(new_body.encode()).hexdigest()
c.execute('update effects set content=?, content_sha256=? where id=?',(new_body,new_hash,row[0]));c.commit();c.close()
r=subprocess.run([sys.executable,str(ROOT/'stage_s_hardened/code/independent_audit.py'),str(dest)],capture_output=True,text=True)
assert r.returncode!=0, 'Tampered SQL unexpectedly passed independently audited evidence!'
res={'test':'SQL_CONTENT_AND_LOCAL_HASH_TAMPER','database':'camm_recipient.sqlite','changed_id':row[0],'changed_fields':['content','content_sha256'],'separate_auditor_rejected':True,'auditor_returncode':r.returncode,'auditor_stderr_tail':r.stderr[-1200:]}
(ROOT/'results/a0_sql_tamper_test.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps({k:v for k,v in res.items() if k!='auditor_stderr_tail'},indent=2))
