"""Regression tests for the fixed legal-clock wording in source-to-effect notes."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
from agent import produce


class ClauseNoteTests(unittest.TestCase):
    def setUp(self):
        snapshot = json.loads((ROOT / 'inputs' / 'source_snapshot.json').read_text())
        self.docs = {(r['case_id'], r['source_id']): r['text'] for r in snapshot['sources']}
        self.num = 0

    def fetch(self, url):
        args = parse_qs(urlsplit(url).query)
        case = args['case'][0]
        source = args['source'][0]
        self.num += 1
        return {'text': self.docs[(case, source)], 'receipt': {'body': {'read_id': self.num}}}

    def test_camm_five_business_days_with_parenthetical_digit(self):
        with patch('agent.get', self.fetch):
            document, receipts, trace = produce('camm', 'test-camm', 'http://fixture', ['PRIV'])
        self.assertIn('five-business-day clawback from producer notice', document['content'])
        self.assertNotIn('unresolved legal clock', document['content'])
        self.assertEqual(len(receipts), 2)
        self.assertEqual(len(trace), 3)

    def test_napoli_seven_calendar_days(self):
        with patch('agent.get', self.fetch):
            document, receipts, trace = produce('napoli', 'test-napoli', 'http://fixture', ['CLEAN'])
        self.assertIn('seven-day return clock from producer notice', document['content'])
        self.assertNotIn('unresolved legal clock', document['content'])
        self.assertEqual(len(receipts), 2)
        self.assertEqual(len(trace), 3)


if __name__ == '__main__':
    unittest.main()
