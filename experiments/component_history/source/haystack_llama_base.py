#!/usr/bin/env python3
import json
from importlib.metadata import version

def haystack_case():
    from haystack import Document
    from haystack.document_stores.in_memory import InMemoryDocumentStore
    ds=InMemoryDocumentStore()
    docs=[
      Document(id='src-rev',content='R_src',meta={'kind':'source','dep':'rev'}),
      Document(id='src-clean',content='K_src',meta={'kind':'source','dep':'clean'}),
      Document(id='der-mixed',content='R_src K_src derived',meta={'kind':'derived','dep':'rev+clean'}),
      Document(id='der-clean',content='K_src only derived',meta={'kind':'derived','dep':'clean'})]
    ds.write_documents(docs)
    ds.delete_documents(['src-rev'])
    after=ds.filter_documents()
    ids=sorted(d.id for d in after)
    ds.delete_documents(['der-mixed'])
    post=sorted(d.id for d in ds.filter_documents())
    return {'version':version('haystack-ai'),'after_source_delete_ids':ids,
      'derived_rev_survives_source_delete':'der-mixed' in ids,
      'clean_survives_source_delete':'src-clean' in ids and 'der-clean' in ids,
      'explicit_descendant_cleanup_preserves_clean':'der-mixed' not in post and 'src-clean' in post and 'der-clean' in post,
      'automatic_cascade':False if 'der-mixed' in ids else True,
      'native_delete_granularity':'document_ids'}

def llama_case():
    from llama_index.core import VectorStoreIndex, Document
    from llama_index.core.embeddings import MockEmbedding
    emb=MockEmbedding(embed_dim=4)
    docs=[
      Document(text='R_src',doc_id='src-rev',metadata={'kind':'source','dep':'rev'}),
      Document(text='K_src',doc_id='src-clean',metadata={'kind':'source','dep':'clean'}),
      Document(text='R_src K_src derived',doc_id='der-mixed',metadata={'kind':'derived','dep':'rev+clean'}),
      Document(text='K_src only derived',doc_id='der-clean',metadata={'kind':'derived','dep':'clean'})]
    ix=VectorStoreIndex.from_documents(docs,embed_model=emb)
    before=sorted(ix.ref_doc_info.keys())
    ix.delete_ref_doc('src-rev',delete_from_docstore=True)
    after=sorted(ix.ref_doc_info.keys())
    # second explicit ref-doc cleanup; no automatic provenance inference across independent ref docs
    ix.delete_ref_doc('der-mixed',delete_from_docstore=True)
    post=sorted(ix.ref_doc_info.keys())
    return {'version':version('llama-index-core'),'before_ref_docs':before,'after_source_delete_ref_docs':after,
      'source_ref_removed':'src-rev' not in after,
      'derived_rev_survives_source_delete':'der-mixed' in after,
      'clean_survives_source_delete':'src-clean' in after and 'der-clean' in after,
      'explicit_descendant_cleanup_preserves_clean':'der-mixed' not in post and 'src-clean' in post and 'der-clean' in post,
      'automatic_cross_ref_cascade':False if 'der-mixed' in after else True,
      'native_delete_granularity':'ref_doc -> associated nodes'}

def langgraph_case():
    from typing_extensions import TypedDict
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    class S(TypedDict):
        source_marker:str
        clean_marker:str
        derived:str
    def step(s:S): return {'derived':'D['+s['source_marker']+']|K['+s['clean_marker']+']'}
    saver=InMemorySaver(); b=StateGraph(S); b.add_node('step',step); b.add_edge(START,'step'); b.add_edge('step',END)
    g=b.compile(checkpointer=saver); cfg={'configurable':{'thread_id':'t1'}}
    g.invoke({'source_marker':'R_src','clean_marker':'K_src','derived':''},cfg)
    state=g.get_state(cfg).values
    before=list(saver.list({'configurable':{'thread_id':'t1'}}))
    # external source deletion has no source-addressed checkpoint operation; state remains until coarse thread deletion.
    retains_rev='R_src' in json.dumps(state,sort_keys=True)
    retains_clean='K_src' in json.dumps(state,sort_keys=True)
    saver.delete_thread('t1')
    after=list(saver.list({'configurable':{'thread_id':'t1'}}))
    return {'version':version('langgraph'),'checkpoint_count_before':len(before),
      'checkpoint_retains_revoked_marker_after_external_source_delete':retains_rev,
      'checkpoint_retains_clean_marker_before_thread_delete':retains_clean,
      'thread_delete_remaining_checkpoints':len(after),
      'thread_delete_removes_clean_state_too':len(after)==0,
      'native_delete_granularity':'thread (all checkpoints/writes)'}

def main():
    out={'haystack':haystack_case(),'llamaindex':llama_case(),'langgraph':langgraph_case()}
    print('RESULT',json.dumps(out,sort_keys=True))
    assert out['haystack']['derived_rev_survives_source_delete']
    assert out['llamaindex']['source_ref_removed'] and out['llamaindex']['derived_rev_survives_source_delete']
    assert out['langgraph']['checkpoint_retains_revoked_marker_after_external_source_delete'] and out['langgraph']['thread_delete_removes_clean_state_too']
if __name__=='__main__': main()
