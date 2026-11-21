#!/usr/bin/env python3
import json
from importlib.metadata import version

def make_llama_index():
    from llama_index.core import VectorStoreIndex, Document
    from llama_index.core.embeddings import MockEmbedding
    emb=MockEmbedding(embed_dim=4)
    docs=[
      Document(text='R_src',doc_id='src-rev'),
      Document(text='K_src',doc_id='src-clean'),
      Document(text='R_src K_src derived',doc_id='der-mixed'),
      Document(text='K_src derived',doc_id='der-clean')]
    return VectorStoreIndex.from_documents(docs,embed_model=emb)

def llama_default_vs_strict():
    ix=make_llama_index()
    pre=sorted(ix.ref_doc_info.keys())
    ix.delete_ref_doc('src-rev')
    default_view=sorted(ix.ref_doc_info.keys())
    info=ix.docstore.get_ref_doc_info('src-rev')
    residual_nodes=[] if info is None else list(info.node_ids)
    residual_retrievable=0
    for nid in residual_nodes:
        try:
            n=ix.docstore.get_document(nid,raise_error=False)
        except TypeError:
            try: n=ix.docstore.get_document(nid)
            except Exception: n=None
        if n is not None: residual_retrievable+=1

    ix2=make_llama_index()
    ix2.delete_ref_doc('src-rev',delete_from_docstore=True)
    strict_view=sorted(ix2.ref_doc_info.keys())
    strict_info=ix2.docstore.get_ref_doc_info('src-rev')
    return {
      'version':version('llama-index-core'),
      'before_ref_docs':pre,
      'default_index_view_source_removed':'src-rev' not in default_view,
      'default_independent_derived_survives':'der-mixed' in default_view,
      'default_docstore_ref_info_survives':info is not None,
      'default_docstore_residual_node_count':len(residual_nodes),
      'default_docstore_retrievable_node_count':residual_retrievable,
      'strict_index_view_source_removed':'src-rev' not in strict_view,
      'strict_docstore_ref_info_removed':strict_info is None,
      'strict_independent_derived_survives':'der-mixed' in strict_view,
      'documented_default_delete_from_docstore':False}

def langgraph_history_case():
    from typing_extensions import TypedDict
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    class S(TypedDict):
        source_marker:str
        clean_marker:str
        derived:str
    def step(s:S): return {'derived':'D['+s['source_marker']+']|K['+s['clean_marker']+']'}
    saver=InMemorySaver(); b=StateGraph(S); b.add_node('step',step); b.add_edge(START,'step'); b.add_edge('step',END)
    g=b.compile(checkpointer=saver); cfg={'configurable':{'thread_id':'t-hist'}}
    g.invoke({'source_marker':'R_src','clean_marker':'K_src','derived':''},cfg)
    before=list(saver.list(cfg))
    g.update_state(cfg,{'source_marker':'','derived':'K[K_src]'})
    latest=g.get_state(cfg).values
    hist=list(saver.list(cfg))
    hist_text=[json.dumps(t.checkpoint,sort_keys=True,default=str) for t in hist]
    old_rev=sum('R_src' in x for x in hist_text)
    old_clean=sum('K_src' in x for x in hist_text)
    # cleanup at native InMemorySaver thread granularity
    saver.delete_thread('t-hist')
    remaining=list(saver.list(cfg))
    return {
      'version':version('langgraph'),
      'checkpoint_count_before_current_repair':len(before),
      'latest_current_state_has_revoked_marker':'R_src' in json.dumps(latest,sort_keys=True),
      'latest_current_state_has_clean_marker':'K_src' in json.dumps(latest,sort_keys=True),
      'history_checkpoint_count_after_current_repair':len(hist),
      'history_checkpoints_with_revoked_marker':old_rev,
      'history_checkpoints_with_clean_marker':old_clean,
      'thread_delete_remaining_checkpoints':len(remaining),
      'thread_delete_removes_clean_history_too':len(remaining)==0}

def haystack_filter_case():
    from haystack import Document
    from haystack.document_stores.in_memory import InMemoryDocumentStore
    ds=InMemoryDocumentStore(shared=False)
    ds.write_documents([
      Document(id='src-rev',content='R',meta={'dep':'rev'}),
      Document(id='src-clean',content='K',meta={'dep':'clean'}),
      Document(id='der-mixed',content='RK',meta={'dep':'rev+clean'}),
      Document(id='der-clean',content='K2',meta={'dep':'clean'})])
    filt={'field':'meta.dep','operator':'==','value':'rev+clean'}
    matched=sorted(d.id for d in ds.filter_documents(filters=filt))
    has=hasattr(ds,'delete_by_filter')
    deleted=ds.delete_by_filter(filt) if has else None
    remain=sorted(d.id for d in ds.filter_documents())
    return {
      'version':version('haystack-ai'),
      'has_delete_by_filter':has,
      'filter_matched_ids':matched,
      'delete_by_filter_result':deleted,
      'remaining_ids':remain,
      'filter_cleanup_preserved_clean':'src-clean' in remain and 'der-clean' in remain,
      'whole_mixed_document_removed':'der-mixed' not in remain}

def main():
    out={'llama_default_vs_strict':llama_default_vs_strict(),'langgraph_history':langgraph_history_case(),'haystack_filter':haystack_filter_case()}
    print('RESULT',json.dumps(out,sort_keys=True))
    L=out['llama_default_vs_strict']
    assert L['default_index_view_source_removed'] and L['default_docstore_ref_info_survives']
    assert L['strict_index_view_source_removed'] and L['strict_docstore_ref_info_removed']
    G=out['langgraph_history']
    assert not G['latest_current_state_has_revoked_marker'] and G['latest_current_state_has_clean_marker']
    assert G['history_checkpoints_with_revoked_marker']>0
    H=out['haystack_filter']
    assert H['has_delete_by_filter'] and H['whole_mixed_document_removed'] and H['filter_cleanup_preserved_clean']
if __name__=='__main__': main()
