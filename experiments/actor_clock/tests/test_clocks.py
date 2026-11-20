import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stage_r.law import deadline,evaluate_due,TEST_CLOSED_DATES,load_duties

class CalendarTests(unittest.TestCase):
    def test_eight_typed_duties(self):
        duties=load_duties();self.assertEqual(len(duties),8)
        self.assertEqual({d.actor for d in duties},{'producing_party','receiving_party','receiving_challenger','receiving_counsel'})
        self.assertTrue(all(d.source_url.startswith('https://') for d in duties))
    def test_iottie_producer_ten_bdays(self):
        self.assertEqual(deadline('2026-11-20',10,'business_days',closed_dates=TEST_CLOSED_DATES),'2026-12-07')
    def test_iottie_challenger_seven_bdays(self):
        self.assertEqual(deadline('2026-12-07',7,'business_days',closed_dates=TEST_CLOSED_DATES),'2026-12-16')
    def test_camm_five_bdays_holiday(self):
        self.assertEqual(deadline('2026-11-20',5,'business_days',closed_dates=TEST_CLOSED_DATES),'2026-11-30')
    def test_napoli_seven_calendar(self):
        self.assertEqual(deadline('2026-11-24',7,'calendar_days',closed_dates=TEST_CLOSED_DATES),'2026-12-01')
    def test_napoli_thirty_calendar(self):
        self.assertEqual(deadline('2026-12-02',30,'calendar_days',closed_dates=TEST_CLOSED_DATES),'2027-01-01')
    def test_napoli_certification_ten_calendar(self):
        self.assertEqual(deadline('2026-12-29',10,'calendar_days',closed_dates=TEST_CLOSED_DATES),'2027-01-08')
    def test_iottie_two_months_rollover(self):
        self.assertEqual(deadline('2026-12-31',2,'months',closed_dates=TEST_CLOSED_DATES),'2027-02-28')
    def test_camm_sixty_calendar(self):
        self.assertEqual(deadline('2027-01-01',60,'calendar_days',closed_dates=TEST_CLOSED_DATES),'2027-03-02')
    def test_unknown_calendar(self):
        self.assertIsNone(deadline('2026-11-20',5,'business_days',closed_dates=None))
        self.assertEqual(evaluate_due('2026-11-20',5,'business_days','2026-12-05',None,closed_dates=None)['status'],'UNRESOLVED_CALENDAR')
    def test_overdue_vs_attestation(self):
        self.assertEqual(evaluate_due('2026-11-24',7,'calendar_days','2026-12-02',None,closed_dates=TEST_CLOSED_DATES)['status'],'OVERDUE_UNATTESTED')
        self.assertEqual(evaluate_due('2026-11-24',7,'calendar_days','2027-01-04','2026-12-29',closed_dates=TEST_CLOSED_DATES)['status'],'ATTESTED_AFTER_WINDOW')
    def test_late_never_grants_use(self):
        # Clock status is descriptive and never returned as an ALLOW_SCOPED permit.
        self.assertEqual(evaluate_due('2026-11-20',5,'business_days','2027-03-01',None,closed_dates=TEST_CLOSED_DATES)['status'],'OVERDUE_UNATTESTED')

if __name__=='__main__':unittest.main()
