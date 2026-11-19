import json
import sqlite3
import unittest
from pathlib import Path

from polyviz.inventory import curated_keys, document, identity_key, issue_labels, passed_records, shorten

ROOT = Path(__file__).resolve().parents[1]


class InventoryTests(unittest.TestCase):
    def test_issue_phrases_stay_unreviewed_proposals(self):
        taxonomy = {'version': '1', 'issue_tags': [{'id': 'data_centers', 'aliases': ['data center']}],
                    'affected_sectors': [], 'policy_actions': []}
        self.assertEqual(issue_labels('Data centers.', 'A data-center facility.', taxonomy), ['data_centers'])
        self.assertEqual(issue_labels('Housing.', 'No matching phrase.', taxonomy), [])
    def test_shorten_keeps_short_text_and_cuts_on_a_word(self):
        self.assertEqual(shorten('Housing bill.'), 'Housing bill.')
        self.assertTrue(shorten('alpha beta gamma', 10).endswith('…'))
        self.assertLessEqual(len(shorten('alpha beta gamma', 10)), 10)

    def test_passed_export_skips_curated_congress_and_other_years(self):
        connection = sqlite3.connect(':memory:')
        connection.execute('''CREATE TABLE bills (
            id TEXT, state TEXT, session_id TEXT, bill_number TEXT, title TEXT,
            summary TEXT, status_date TEXT, source_status TEXT, record_json TEXT)''')
        rows = [
            ('CA-1-AB1', 'CA', '1', 'AB1', 'Keep', 'A housing bill.', '2025-03-02', '4',
             {'source': {'url': 'https://leginfo.legislature.ca.gov/bill'}, 'policy_topics': ['housing', 'invented']}),
            ('CA-1-AB130', 'CA', '1', 'AB130', 'Curated duplicate', 'Already on the map.', '2025-06-01', '4',
             {'source': {'url': 'https://leginfo.legislature.ca.gov/other'}, 'policy_topics': ['housing']}),
            ('US-1-HR1', 'US', '1', 'HR1', 'Congress', 'Not a state.', '2025-03-02', '4',
             {'source': {'url': 'https://congress.gov/bill'}, 'policy_topics': []}),
            ('TX-1-HB1', 'TX', '1', 'HB1', 'Earlier', 'Too early.', '2024-12-01', '4',
             {'source': {'url': 'https://capitol.texas.gov/bill'}, 'policy_topics': []}),
            ('NY-1-S1', 'NY', '1', 'S1', 'Pending', 'Not passed.', '2025-04-01', '1',
             {'source': {'url': 'https://nyassembly.gov/bill'}, 'policy_topics': []}),
        ]
        for row in rows:
            *fields, payload = row
            connection.execute(
                'INSERT INTO bills VALUES (?,?,?,?,?,?,?,?,?)',
                (*fields, json.dumps(payload)))
        skip = {identity_key('CA', 'AB130')}
        records = passed_records(connection, skip=skip, topics={'housing'})
        self.assertEqual([record['id'] for record in records], ['CA-1-AB1'])
        self.assertEqual(records[0]['status'], 'passed')
        self.assertEqual(records[0]['dates'], {'status': '2025-03-02'})
        self.assertEqual(records[0]['policy_topics'], ['housing'])
        self.assertEqual(records[0]['issue_tags'], [])
        self.assertEqual(records[0]['classification']['review_status'], 'unreviewed')
        self.assertTrue(records[0]['sources'][0]['url'].startswith('https://'))
        payload = document(records)
        self.assertEqual(payload['bills'][0][-1], [])
        self.assertEqual(payload['layout'], 'passed-bills-v2')
        self.assertEqual(payload['states'], ['CA'])
        self.assertIn('not verified', payload['coverage'])

    def test_published_inventory_stays_separate_from_source_checked_enactments(self):
        inventory_path = ROOT / 'web' / 'dist' / 'data' / 'inventory.json'
        inventory = json.loads(inventory_path.read_text())
        curated = json.loads((ROOT / 'web' / 'dist' / 'data' / 'bills.json').read_text())
        self.assertEqual(inventory['layout'], 'passed-bills-v2')
        self.assertGreater(len(inventory['bills']), 1000)
        self.assertNotIn('US', inventory['states'])
        self.assertGreaterEqual(len(inventory['states']), 50)
        keys = {identity_key(row[1], row[3]) for row in inventory['bills']}
        self.assertTrue(curated_keys().isdisjoint(keys))
        ids = [row[0] for row in inventory['bills']]
        self.assertEqual(len(ids), len(set(ids)))
        bill_id, state, session_id, number, title, summary, status_date, topics, url, issues = inventory['bills'][0]
        self.assertTrue(status_date.startswith('2025-'))
        self.assertIsInstance(topics, list)
        self.assertIsInstance(issues, list)
        self.assertTrue(bill_id and state and session_id and number and title and summary)
        self.assertTrue(url == '' or url.startswith('https://'))
        allowed = {tag['id'] for tag in json.loads((ROOT / 'web/dist/data/issues.json').read_text())['issue_tags']}
        tagged = [row for row in inventory['bills'] if row[9]]
        self.assertGreater(len(tagged), 0)
        self.assertTrue(all(tag in allowed for row in tagged for tag in row[9]))
