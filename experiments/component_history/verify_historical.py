#!/usr/bin/env python3
"""Independent audit of original recorded component and checkpoint experiments."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = {
    'chroma_qdrant': ('source/chroma_qdrant.py','fe37263b59ed27084751f9c1ee4ee80bfc7d552a'),
    'haystack_llama_base': ('source/haystack_llama_base.py','aeaf20b85871943fd829595a37ae41ba4eae6cfc'),
    'haystack_llama_followup': ('source/haystack_llama_followup.py','9ff9d933d80d4bcac6a99d2842453f68f9a83377'),
    'composed_chroma_langgraph': ('source/composed_chroma_langgraph.py','bf65fd8507f66987042f29cfcb2fd9bde88ca6d5'),
    'postgres_saver': ('source/postgres_saver.py','5e738118f03f8056c43123aadfa7bfee4b163d62'),
    'replay_inmemory': ('source/replay_inmemory.py','1b100479ff1b90de0583e056ea54ede68d64958a'),
    'replay_postgres': ('source/replay_postgres.py','7bc7bdfac3562e92402031f5acb86b655ee30d71'),
}

def original_blob_sha(file: Path) -> str:
    content = file.read_bytes()
    return hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()

def audit(skip_sources=False):
    comp = json.loads((ROOT/'component_results.json').read_text())
    checkpoints = json.loads((ROOT/'checkpoint_results.json').read_text())
    assert comp['schema']=='historical-component-stack-evidence-v1'
    assert comp['source_master_sha256']=='67297e646493146c08dd1ee1b553774acc7c1950a2ddee00dee5b3061ce7784f'
    assert checkpoints['schema']=='historical-checkpoint-effect-records-v1'
    assert set(comp['cases'])==set(CASES)-{'replay_inmemory','replay_postgres'}
    assert set(checkpoints['cases'])=={'inmemory','postgres'}
    for key,(path,sha) in CASES.items():
        if not skip_sources:
            assert original_blob_sha(ROOT/path)==sha,(key,'original Git source changed')
        if key in comp['cases']:
            assert comp['cases'][key]['source_blob_sha1']==sha
    c=comp['cases']
    for store in ('chroma','qdrant'):
        x=c['chroma_qdrant']['result'][store]
        assert x['derived_rev_survives_source_delete'] and x['clean_survives_source_delete']
        assert x['filter_cleanup_removed_mixed'] and x['filter_cleanup_preserved_clean']
        assert x['automatic_cascade'] is False
    main=c['haystack_llama_base']['result']
    assert main['haystack']['version']=='3.3.0'
    assert main['haystack']['derived_rev_survives_source_delete']
    assert main['llamaindex']['version']=='0.14.25'
    assert main['llamaindex']['source_ref_removed']
    assert main['llamaindex']['derived_rev_survives_source_delete']
    assert main['llamaindex']['clean_survives_source_delete']
    follow=c['haystack_llama_followup']['result']
    llama=follow['llama_default_vs_strict']
    assert llama['documented_default_delete_from_docstore'] is False
    assert llama['default_index_view_source_removed']
    assert llama['default_docstore_ref_info_survives']
    assert llama['default_docstore_retrievable_node_count']==1
    assert llama['strict_docstore_ref_info_removed']
    assert llama['strict_independent_derived_survives']
    hf=follow['haystack_filter']
    assert hf['has_delete_by_filter'] and hf['delete_by_filter_result']==1
    assert hf['filter_matched_ids']==['der-mixed'] and hf['whole_mixed_document_removed']
    lg=follow['langgraph_history']
    assert lg['history_checkpoint_count_after_current_repair']==4
    assert lg['history_checkpoints_with_revoked_marker']==3
    assert lg['history_checkpoints_with_clean_marker']==4
    assert lg['latest_current_state_has_revoked_marker'] is False
    assert lg['thread_delete_remaining_checkpoints']==0
    composed=c['composed_chroma_langgraph']['result']
    assert composed['retrieval_clean_after_native_source_delete']
    assert composed['historical_checkpoints_with_revoked_marker_after_current_repair']==3
    assert composed['historical_checkpoints_with_clean_marker_after_current_repair']==4
    assert composed['thread_delete_remaining_checkpoints']==0
    pg=c['postgres_saver']['result']
    assert pg['checkpoint_postgres_version']=='3.1.2'
    assert pg['history_with_revoked']==3 and pg['history_with_clean']==4
    assert pg['after_delete_thread']==0 and pg['latest_has_revoked'] is False
    expected={'no_guard':('allowed',1,True),'entry_only':('allowed',1,True),
      'pre_effect':('blocked',0,False),'clean_independent':('allowed',1,False),
      'unknown_dependency':('unresolved',0,False),
      'false_complete_metadata':('allowed',1,True),
      'release_after_sequester':('blocked',0,False)}
    for mode in ('inmemory','postgres'):
        e=checkpoints['cases'][mode]
        d=e['result']
        assert d['case_count']==7 and d['all_assertions_passed']
        assert d['schema']=='checkpoint-effect-v1' and d['langgraph_version']=='1.2.12'
        if mode=='postgres':assert d['postgres_saver_version']=='3.1.2'
        assert len(d['cases'])==7
        assert {p['name'] for p in d['cases']}==set(expected)
        for p in d['cases']:
            dec,n,unsafe=expected[p['name']]
            assert (p['first_replay_decision'],p['first_replay_new_effects'],
                    p['unauthorized_effect_observed'])==(dec,n,unsafe),p['name']
            assert p['old_checkpoint_retained'] and p['latest_view_repaired']
            assert len(p['rows'])==p['total_effects_after_replays']
        assert sum(x['unauthorized_effect_observed'] for x in d['cases'])==3
    return {'status':'PASS','original_component_runs':len(c),
            'original_checkpoint_replays':14,'source_files':len(CASES),
            'recovered_haystack_and_llamaindex':True,
            'historical_checkpoints_with_revoked_marker':3}

if __name__=='__main__':
    if not __debug__:
        raise SystemExit('Verification requires assertions enabled')
    a=argparse.ArgumentParser()
    a.add_argument('--recorded-only',action='store_true',help='Verify saved outcomes without local original scripts')
    args=a.parse_args()
    print(json.dumps(audit(skip_sources=args.recorded_only),sort_keys=True))
