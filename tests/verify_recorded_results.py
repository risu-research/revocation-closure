#!/usr/bin/env python3
"""Check archived and optional rerun court-policy results without extra packages."""
from pathlib import Path
import hashlib
import json

FROZEN_SHA256="d74a143ba5fccf8c5fdf71d81baa476ee34a908fe23110b04b31a21f2d3ab443"
EXPECTED={
 "acosta_unchecked":(1,True), "acosta_cached":(1,True),
 "acosta_guarded":(0,False), "acosta_clean":(1,False),
 "necec_guarded":(0,False), "necec_unknown":(0,False),
 "necec_false_complete":(1,True), "necec_withdrawn":(1,False)
}
ROOT=Path(__file__).resolve().parents[1]

def check(p, require_digest=False):
    raw=p.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if require_digest:
        assert digest==FROZEN_SHA256,(p,digest)
    r=json.loads(raw)
    assert r["schema"]=="court-grounded-checkpoint-replay-v1"
    assert r["status"]=="PASS"
    assert r["fixture_count"]==r["fixture_passed"]==25
    assert r["replay_count"]==r["replay_passed"]==8
    assert r["deadline_controls_passed"]==2
    assert set(r["source_orders"])=={"acosta","necec","broadway","spheres"}
    assert all(x["pass"] and x["actual"]==x["expected"] for x in r["policy_fixtures"])
    observed={x["name"]:(x["new_writes_from_historical_replay"],x["unauthorized_write_observed"])
              for x in r["replay_results"]}
    assert observed==EXPECTED,(observed,EXPECTED)
    print("VERIFIED",p.name,digest,"fixtures=25,replays=8")

check(ROOT/"results/court_policy_result.json",True)
rerun=ROOT/"legal_order_result.json"
if rerun.exists():
    check(rerun)
