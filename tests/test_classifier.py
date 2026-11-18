import json
import unittest
from polyviz.classifier import TAXONOMY, classify, convert


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = json.loads(TAXONOMY.read_text())
        self.bill = {'state':'CA', 'session_id':'2025-REGULAR',
                     'bill_number':'AB 123', 'title':'Affordable housing tax credits',
                     'status':'pending'}

    def test_overlapping_topics_and_evidence(self):
        result = convert(self.bill, self.taxonomy)
        self.assertEqual(result['topics'], ['housing', 'taxation'])
        self.assertIn('housing', result['classification']['evidence']['housing'])
        self.assertEqual(result['id'], 'CA-2025-REGULAR-AB123')

    def test_word_boundaries_and_unknown(self):
        result = classify('Taxi learning environment', '', self.taxonomy)
        self.assertEqual(result['topics'], [])
        self.assertEqual(result['classification']['outcome'], 'unclassified')

    def test_case_punctuation_and_summary(self):
        result = classify('An act', 'MENTAL-HEALTH and public transit.', self.taxonomy)
        self.assertEqual(result['topics'], ['healthcare', 'transportation'])

    def test_special_sessions_have_distinct_ids(self):
        first = convert(self.bill, self.taxonomy)
        self.bill['session_id'] = '2025-SPECIAL1'
        self.assertNotEqual(first['id'], convert(self.bill, self.taxonomy)['id'])

    def test_legiscan_passed_not_automatically_enacted(self):
        payload = {'status':'OK', 'bill': {'state':'TX','session':{'session_id':2000},
                   'bill_id':100, 'bill_number':'HB1', 'title':'Education', 'status':4}}
        result = convert(payload, self.taxonomy)
        self.assertEqual(result['status'], 'unknown')
        self.assertTrue(result['warnings'])
        self.assertEqual(result['source']['provider'], 'legiscan')

    def test_invalid_metadata_rejected(self):
        for field, value in [('state','ZZ'), ('bill_number',''), ('status','passed'),
                             ('session_id','2025 regular'), ('title',None)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                convert({**self.bill, field:value}, self.taxonomy)


if __name__ == '__main__':
    unittest.main()
