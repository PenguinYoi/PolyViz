from copy import deepcopy
import json
from pathlib import Path
import unittest
from polyviz.schema import to_v2,migrate,ISSUES
from polyviz.classifier import TAXONOMY


class SchemaTests(unittest.TestCase):
    def test_migration_preserves_identity_and_labels_without_inference(self):
        source={'schema_version':1,'bills':[{'id':'VA-2025-HB1','topics':['energy'],'title':'Data centers','enacted_date':'2025-07-01'}]}
        before=deepcopy(source);result=migrate(source)
        self.assertEqual(source,before)
        bill=result['bills'][0]
        self.assertEqual(bill['id'],source['bills'][0]['id'])
        self.assertEqual(bill['policy_topics'],['energy'])
        self.assertEqual(bill['dates']['enacted'],'2025-07-01')
        self.assertEqual(bill['issue_tags'],[])
        self.assertNotIn('issue_classification',bill)
        self.assertEqual(migrate(result),result)

    def test_candidate_evidence_is_exact_and_does_not_assign_actions(self):
        r=to_v2({'title':'Data-center water use','summary':'Repeals the rule that requires reporting.','topics':['environment']},detect=True)
        self.assertEqual(r['policy_actions'],[])
        self.assertEqual(r['affected_sectors'],[])
        candidates=r['issue_classification']['candidates']
        self.assertIn('data_centers',[c['label'] for c in candidates])
        self.assertIn('requires_reporting',[c['label'] for c in candidates])
        text=r['title']+'\n'+r['summary']
        for c in candidates:self.assertEqual(text[c['start']:c['end']],c['excerpt'])
        self.assertEqual(r['topics'],['environment'])

    def test_no_match_is_unresolved_not_outside_taxonomy(self):
        r=to_v2({'title':'Unspecified administrative changes','topics':[]},detect=True)
        self.assertEqual(r['issue_classification']['outcome'],'unresolved')

    def test_conflicting_labels_and_dates_are_rejected(self):
        with self.assertRaises(ValueError):to_v2({'topics':['energy'],'policy_topics':['education']})
        with self.assertRaises(ValueError):to_v2({'enacted_date':'2025-01-01','dates':{'enacted':'2025-02-01'}})
        with self.assertRaises(ValueError):to_v2({'dates':{'effective':'bad'}})

    def test_taxonomy_ids_and_boundaries(self):
        t=json.loads(TAXONOMY.read_text());self.assertEqual(len(t['topics']),16)
        for axis in [t['topics']]+[json.loads(ISSUES.read_text())[key] for key in ('issue_tags','affected_sectors','policy_actions')]:
            self.assertEqual(len({x['id'] for x in axis}),len(axis))
            for label in axis:self.assertTrue(label['description'])
        for label in t['topics']:
            self.assertTrue(label['include']);self.assertTrue(label['exclude'])
