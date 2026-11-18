from copy import deepcopy
import json
from pathlib import Path
import unittest
from polyviz.map_data import validate,official_url

SOURCE=Path(__file__).resolve().parents[1]/'web/dist/data/bills.json'


class MapDataTests(unittest.TestCase):
    def setUp(self):self.document=json.loads(SOURCE.read_text())

    def test_sample_provenance_passes_without_claiming_accuracy(self):
        r=validate(self.document)
        self.assertEqual(r['bills'],17)
        self.assertEqual(r['independently_reviewed_labels'],0)

    def test_invalid_sources_dates_and_label_promotion_are_rejected(self):
        for field,value in [('sources',[]),('policy_topics',['invented']),('classification',{'review_status':'reviewed'}),('source_claims',[])]:
            with self.subTest(field=field):
                d=deepcopy(self.document);d['bills'][0][field]=value
                with self.assertRaises(ValueError):validate(d)
        d=deepcopy(self.document);d['bills'][0]['dates']['enacted']='2025-99-30'
        with self.assertRaises(ValueError):validate(d)

    def test_evidence_must_belong_to_declared_sources(self):
        d=deepcopy(self.document);d['bills'][0]['source_claims'][0]['source_url']='https://example.org/'
        with self.assertRaises(ValueError):validate(d)

    def test_official_domain_check_rejects_lookalikes(self):
        self.assertTrue(official_url('https://capitol.texas.gov/example'))
        self.assertFalse(official_url('https://capitol.texas.gov.example.org/'))
        self.assertFalse(official_url('https://evil.ca.gov@example.org/'))

    def test_multiple_effective_dates_cannot_be_flattened(self):
        d=deepcopy(self.document);b=next(b for b in d['bills'] if b['bill_number']=='SB38')
        self.assertEqual(len(b['effective_date_events']),2)
        b['dates']['effective']='2026-01-01'
        with self.assertRaises(ValueError):validate(d)

    def test_duplicate_identities_are_rejected(self):
        self.document['bills'].append(deepcopy(self.document['bills'][0]))
        with self.assertRaises(ValueError):validate(self.document)
