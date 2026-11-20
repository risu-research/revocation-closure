"""Separate Linux non-root recipient exposing exactly signed event/effect messages.
An independent SQLite file belongs to this process. Test-only clock changes are
restricted to orchestrator UID 0 by kernel SO_PEERCRED.
"""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from stage_r.recipient import LegalRecipient
from stage_r.law import ROLES

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor_stage_q'))
from experiments.enforced_custody.ipc import serve

def main():
    p=argparse.ArgumentParser()
    for k in ('socket','ready','db','trust'):p.add_argument('--'+k,required=True)
    p.add_argument('--recipient-uid',type=int,default=23323)
    p.add_argument('--worker-uid',type=int,default=23321)
    a=p.parse_args()
    if os.geteuid()!=a.recipient_uid or a.recipient_uid in (0,a.worker_uid):
        raise PermissionError('Recipient must be isolated non-root identity')
    r=LegalRecipient(Path(a.db),json.loads(Path(a.trust).read_text()),'2026-11-19')
    def handler(msg:dict,uid:int):
        cmd=msg.get('cmd')
        print('SERVER ENTER',cmd,'UID',uid,flush=True,file=sys.stderr)
        if cmd in {'set_clock','set_calendar','snapshot','ping'}:
            if uid!=0:raise PermissionError('Trusted fixture control requires root peer UID')
            if cmd=='set_clock':
                if set(msg)!={'cmd','date'}:raise ValueError('set_clock shape')
                r.set_clock_trusted(msg['date']);return {'date':r.now}
            if cmd=='set_calendar':
                if set(msg)!={'cmd','enabled'}:raise ValueError('set_calendar shape')
                r.set_calendar_trusted(msg['enabled']);return {'enabled':r.calendar_enabled}
            if cmd=='snapshot':
                if set(msg)!={'cmd','case'}:raise ValueError('snapshot shape')
                return {'case':msg['case'],'date':r.now,'duties':r.obligations(msg['case']),'epoch':r._epoch()}
            return {'uid':os.geteuid(),'date':r.now}
        if cmd=='event':
            if set(msg)!={'cmd','envelope'}:raise ValueError('event shape')
            return r.record_event(msg['envelope'])
        if cmd=='effect':
            if set(msg)!={'cmd','bundle','actor_envelope','claimed','cached'}:raise ValueError('effect shape')
            return r.attempt(msg['bundle'],msg['actor_envelope'],msg['claimed'],msg['cached'])
        if cmd=='challenge_copy':
            if set(msg)!={'cmd','case','source_id','actor_envelope'}:
                raise ValueError('challenge_copy shape')
            return r.challenge_copy(msg['case'],msg['source_id'],msg['actor_envelope'])
        if cmd=='archive':
            if set(msg)!={'cmd','case','note_id','actor_envelope','qualified','contains_specified'}:
                raise ValueError('archive shape')
            value=r.archive(msg['case'],msg['note_id'],msg['actor_envelope'],msg['qualified'],msg['contains_specified'])
            print('SERVER ARCHIVE RETURN',value,flush=True,file=sys.stderr)
            return value
        raise ValueError('No route for command')
    try:serve(a.socket,{0,a.worker_uid},handler,a.ready)
    finally:r.close()

if __name__=='__main__':main()
