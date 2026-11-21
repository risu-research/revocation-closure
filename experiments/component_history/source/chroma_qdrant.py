#!/usr/bin/env python3
import json,time,urllib.request,urllib.error,sys

def req(method,url,obj=None):
    data=None if obj is None else json.dumps(obj).encode()
    r=urllib.request.Request(url,data=data,method=method,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(r,timeout=20) as x:
        b=x.read().decode()
        return json.loads(b) if b else None

def wait(url,tries=80):
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url,timeout=2) as r:
                if r.status<500: return
        except Exception: time.sleep(.5)
    raise RuntimeError('timeout '+url)

def chroma():
    base='http://127.0.0.1:8000/api/v2'
    wait(base+'/heartbeat')
    p=base+'/tenants/default_tenant/databases/default_database/collections'
    c=req('POST',p,{'name':'jmatrix','get_or_create':True})
    cid=c['id']
    root=p+'/'+cid
    # source records and independently materialized derived records in the same real store
    ids=['src-rev','src-clean','der-mixed','der-clean']
    docs=['R_src','K_src','R_src K_src derived','K_src only derived']
    embs=[[1.,0.],[0.,1.],[.7,.7],[0.,.9]]
    metas=[{'kind':'source','dep':'rev'},{'kind':'source','dep':'clean'},{'kind':'derived','dep':'rev+clean'},{'kind':'derived','dep':'clean'}]
    req('POST',root+'/add',{'ids':ids,'documents':docs,'embeddings':embs,'metadatas':metas})
    before=req('POST',root+'/get',{'ids':ids,'include':['documents','metadatas']})
    req('POST',root+'/delete',{'ids':['src-rev']})
    after=req('POST',root+'/get',{'ids':ids,'include':['documents','metadatas']})
    # explicit application-level descendant cleanup by metadata filter is possible only if dependency was stored
    req('POST',root+'/delete',{'where':{'dep':{'$eq':'rev+clean'}}})
    post=req('POST',root+'/get',{'ids':ids,'include':['documents','metadatas']})
    return {
      'before_ids':before['ids'],
      'after_source_delete_ids':after['ids'],
      'derived_rev_survives_source_delete':'der-mixed' in after['ids'],
      'clean_survives_source_delete':'src-clean' in after['ids'] and 'der-clean' in after['ids'],
      'filter_cleanup_removed_mixed':'der-mixed' not in post['ids'],
      'filter_cleanup_preserved_clean':'src-clean' in post['ids'] and 'der-clean' in post['ids'],
      'automatic_cascade':False if 'der-mixed' in after['ids'] else True,
      'granularity':'record/filter'
    }

def qdrant():
    base='http://127.0.0.1:6333'
    wait(base+'/')
    req('PUT',base+'/collections/jmatrix',{'vectors':{'size':2,'distance':'Cosine'}})
    pts=[
      {'id':1,'vector':[1.,0.],'payload':{'name':'src-rev','kind':'source','dep':'rev','text':'R_src'}},
      {'id':2,'vector':[0.,1.],'payload':{'name':'src-clean','kind':'source','dep':'clean','text':'K_src'}},
      {'id':3,'vector':[.7,.7],'payload':{'name':'der-mixed','kind':'derived','dep':'rev+clean','text':'R_src K_src derived'}},
      {'id':4,'vector':[0.,.9],'payload':{'name':'der-clean','kind':'derived','dep':'clean','text':'K_src only derived'}}]
    req('PUT',base+'/collections/jmatrix/points?wait=true',{'points':pts})
    req('POST',base+'/collections/jmatrix/points/delete?wait=true',{'points':[1]})
    after=req('POST',base+'/collections/jmatrix/points/scroll',{'limit':10,'with_payload':True,'with_vector':False})
    names=[p['payload']['name'] for p in after['result']['points']]
    # explicit dependency-aware cleanup by payload filter
    req('POST',base+'/collections/jmatrix/points/delete?wait=true',{'filter':{'must':[{'key':'dep','match':{'value':'rev+clean'}}]}})
    post=req('POST',base+'/collections/jmatrix/points/scroll',{'limit':10,'with_payload':True,'with_vector':False})
    names2=[p['payload']['name'] for p in post['result']['points']]
    return {
      'after_source_delete_ids':sorted(names),
      'derived_rev_survives_source_delete':'der-mixed' in names,
      'clean_survives_source_delete':'src-clean' in names and 'der-clean' in names,
      'filter_cleanup_removed_mixed':'der-mixed' not in names2,
      'filter_cleanup_preserved_clean':'src-clean' in names2 and 'der-clean' in names2,
      'automatic_cascade':False if 'der-mixed' in names else True,
      'granularity':'point/filter'
    }

def main():
    out={'chroma':chroma(),'qdrant':qdrant()}
    print('RESULT',json.dumps(out,sort_keys=True))
    assert out['chroma']['derived_rev_survives_source_delete']
    assert out['qdrant']['derived_rev_survives_source_delete']
    assert out['chroma']['filter_cleanup_removed_mixed'] and out['qdrant']['filter_cleanup_removed_mixed']

if __name__=='__main__': main()
