#!/usr/bin/env python3
"""Standard-library audit of the complete public provenance stress output."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SUMMARY=ROOT/"results"/"provenance_stress_summary.json"
SOURCE=ROOT/"experiments"/"provenance_stress"/"provenance_stress.py"

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(result_path, strict=False):
    ref=json.loads(SUMMARY.read_text())
    data=json.loads(result_path.read_text())
    part=data["partition"]
    assert part in {"dev","holdout"}
    record=ref["development" if part=="dev" else "evaluation"]
    assert digest(SOURCE)==ref["code_sha256"]
    if strict:
        assert digest(result_path)==record["result_sha256"]
    assert data["passed"] is True
    assert data["schema"]=="provenance-fault-evaluation-v1"
    assert data["langgraph_version"]=="1.2.12"
    assert data["guard_names"]==["cached","embedded","receipt"]
    assert data["cases_per_order"]==18
    assert data["orders"]==["acosta","necec"]
    assert data["seeds"]==(ref["protocol"]["development_seeds"] if part=="dev"
                           else ref["protocol"]["evaluation_seeds"])
    assert len(data["records"])==record["checks"]==len(data["seeds"])*2*18*3
    assert data["indistinguishable_pair_checks"]==record["collision_checks"]

    recompute={}
    for g in data["guard_names"]:
        rr=[r for r in data["records"] if r["guard"]==g]
        af=[r for r in rr if r["oracle_affected"]]
        cl=[r for r in rr if not r["oracle_affected"]]
        for r in rr:
            assert r["old_checkpoint_used"] and r["latest_state_repaired"]
            assert r["new_writes"]==(1 if r["decision"]=="ALLOW" else 0)
            assert r["unauthorized_effect"]==(r["oracle_affected"] and r["new_writes"]>0)
            assert r["clean_effect_preserved"]==(not r["oracle_affected"] and r["new_writes"]>0)
            assert r["unknown_decision"]==(r["decision"]=="UNRESOLVED")
        recompute[g]={
            "total":len(rr),"affected":len(af),"clean":len(cl),
            "unauthorized_effects":sum(r["unauthorized_effect"] for r in af),
            "clean_effects_preserved":sum(r["clean_effect_preserved"] for r in cl),
            "unresolved_affected":sum(r["unknown_decision"] for r in af),
            "unresolved_clean":sum(r["unknown_decision"] for r in cl)
        }
    assert recompute==data["summary"]["by_guard"]==record["by_guard"]
    index={(r["order"],r["seed"],r["template"],r["guard"]):r for r in data["records"]}
    for order in data["orders"]:
        for seed in data["seeds"]:
            for guard in data["guard_names"]:
                a=index[(order,seed,"indistinguishable_revoked",guard)]
                b=index[(order,seed,"indistinguishable_clean",guard)]
                assert a["id"]==b["id"] and a["decision"]==b["decision"]
                assert a["new_writes"]==b["new_writes"]
                assert a["oracle_affected"] is True and b["oracle_affected"] is False
    print("VERIFIED",part,len(data["records"]),"replays",len(data["seeds"])*2*3,
          "collision-pair comparisons","sha256",digest(result_path))
    return recompute

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("result_json",type=Path)
    ap.add_argument("--strict-hash",action="store_true",help="Require byte identity to the pinned Actions artifact")
    a=ap.parse_args()
    verify(a.result_json,a.strict_hash)
