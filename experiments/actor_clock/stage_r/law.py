"""Manual, non-authoritative projection of eight selected, source-linked court duties.

These duties and the fixture calendar are an experimental model, not legal advice or
an automated determination that a party satisfied an entered protective order.
"""
from __future__ import annotations
import calendar
import csv
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = {'producing_party', 'receiving_party', 'receiving_challenger', 'receiving_counsel', 'court_event_attester'}
EVENT_ROLES = {
    'producer_notice': 'producing_party',
    'receipt_of_log_and_replacement': 'receiving_challenger',
    'final_termination': 'court_event_attester',
    'return_or_destruction': 'receiving_party',
    'self_discovery': 'receiving_party',
    'producer_log_delivered': 'producing_party',
    'challenge_filed': 'receiving_challenger',
    'written_confirmation': 'receiving_counsel',
}
# These dates are deliberately specified test-calendar exclusions, not a claim about
# real court-business days or official federal/judicial holiday schedules.
TEST_CLOSED_DATES = frozenset({'2026-11-26', '2026-12-25'})

@dataclass(frozen=True)
class Duty:
    case: str
    clause: str
    event: str
    actor: str
    action: str
    amount: int
    unit: str
    source_url: str


def load_duties() -> tuple[Duty,...]:
    path=ROOT/'source_stage_n'/'R2_CLAUSE_CLOCK_AND_IMPLEMENTATION_REGISTER.csv'
    duties=[]
    with path.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            duties.append(Duty(row['case'],row['clause'],row['clock_start'],row['duty_bearer'],
                               row['action'],int(row['amount']),row['unit'],row['source_url']))
    assert len(duties)==8
    assert {(d.case,d.event,d.actor,d.amount,d.unit) for d in duties}.__len__()==8
    return tuple(duties)


def parsedate(v: str) -> dt.date:
    if not isinstance(v,str) or len(v)!=10: raise ValueError('Must supply ISO 8601 YYYY-MM-DD')
    return dt.date.fromisoformat(v)


def deadline(start: str, amount: int, unit: str, *, closed_dates: set[str]|frozenset[str]|None) -> str|None:
    day=parsedate(start)
    if unit=='calendar_days':return (day+dt.timedelta(days=amount)).isoformat()
    if unit=='months':
        y=day.year+(day.month-1+amount)//12
        m=(day.month-1+amount)%12+1
        return dt.date(y,m,min(day.day,calendar.monthrange(y,m)[1])).isoformat()
    if unit=='business_days':
        if closed_dates is None:return None
        n=0
        while n<amount:
            day+=dt.timedelta(days=1)
            if day.weekday()<5 and day.isoformat() not in closed_dates:n+=1
        return day.isoformat()
    raise ValueError('Unsupported court clock unit: '+unit)


def evaluate_due(start: str, amount: int, unit: str, asof: str,
                 completion: str|None, *, closed_dates) -> dict:
    due=deadline(start,amount,unit,closed_dates=closed_dates)
    if due is None:status='UNRESOLVED_CALENDAR'
    elif completion is not None:status='ATTESTED_WITHIN_WINDOW' if completion<=due else 'ATTESTED_AFTER_WINDOW'
    elif asof>due:status='OVERDUE_UNATTESTED'
    elif asof==due:status='DUE_TODAY_UNATTESTED'
    else:status='OPEN_UNATTESTED'
    return {'due':due,'status':status,'start':start,'completion':completion}


def counterpart_completion(d: Duty) -> str|None:
    if d.case=='iottie' and d.event=='producer_notice':return 'producer_log_delivered'
    if d.case=='iottie' and d.event=='receipt_of_log_and_replacement':return 'challenge_filed'
    if d.case=='napoli' and d.event=='return_or_destruction':return 'written_confirmation'
    return 'return_or_destruction' if d.event in {'producer_notice','final_termination'} else None
