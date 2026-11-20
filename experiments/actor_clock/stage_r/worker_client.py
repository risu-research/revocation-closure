import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor_stage_q'))
from experiments.enforced_custody.ipc import client
print(json.dumps(client(sys.argv[1],json.load(sys.stdin)),sort_keys=True))
