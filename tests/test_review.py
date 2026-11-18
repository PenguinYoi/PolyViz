import copy
import json
import unittest
from polyviz.classifier import TAXONOMY
from polyviz.review import initialize,annotate,export_reference,validate_session


class ReviewTests(unittest.TestCase):
    def setUp(self):
        policy=json.loads(TAXONOMY.read_text())
        self.session=initialize([{'state':'CA','session_id':'TEST','bill_number':'AB1',
                                 'title':'Housing assistance','summary':'Funds rental housing.'}],policy)
        self.id=self.session['records'][0]['id']

    def test_blind_session_does_not_prepopulate_labels(self):
        record=self.session['records'][0]
        self.assertIsNone(record['topics'])
        self.assertEqual(record['outcome'],'pending')
        self.assertNotIn('classification',record)
        with self.assertRaises(ValueError): export_reference(self.session)

    def test_invalid_evidence_does_not_modify_session(self):
        before=copy.deepcopy(self.session)
        with self.assertRaises(ValueError):
            annotate(self.session,self.id,'assigned',['housing'],{'housing':'fabricated quote'},'rationale','test')
        self.assertEqual(self.session,before)

    def test_unresolved_is_never_exported_as_empty_label(self):
        annotate(self.session,self.id,'needs_more_text',[],{},'Need details.','test')
        self.assertIsNone(self.session['records'][0]['topics'])
        with self.assertRaises(ValueError): export_reference(self.session,True)

    def test_valid_export_and_history(self):
        annotate(self.session,self.id,'assigned',['housing'],{'housing':'rental housing'},'Rental funding.','test')
        result=export_reference(self.session)
        self.assertEqual(result['labels'][self.id],['housing'])
        self.assertEqual(result['annotations'][self.id]['review_status'],'user_submitted')
        annotate(self.session,self.id,'outside_taxonomy',[],{},'Test revision.','test')
        self.assertEqual(len(self.session['records'][0]['history']),1)
        self.assertEqual(export_reference(self.session)['labels'][self.id],[])

    def test_sectors_are_distinct_from_policy_topics(self):
        self.session['policy']['sectors']=[{'id':'healthcare'}]
        from polyviz.review import digest
        self.session['policy_hash']=digest(self.session['policy'])
        annotate(self.session,self.id,'assigned',['housing'],{'housing':'Housing'},
                 'Separate labels.','test',['healthcare'],{'healthcare':'rental housing'})
        exported=export_reference(self.session)
        self.assertEqual(exported['labels'][self.id],['housing'])
        self.assertEqual(exported['affected_sectors'][self.id],['healthcare'])
        # Excerpt checks verify provenance, not substantive correctness of a human label.
        before=copy.deepcopy(self.session)
        with self.assertRaises(ValueError):
            annotate(self.session,self.id,'assigned',['housing'],{'housing':'Housing'},
                     'Invalid sector.','test',['unknown'],{'unknown':'Housing'})
        self.assertEqual(self.session,before)

    def test_policy_and_input_tampering_detected(self):
        self.session['policy']['version']='modified'
        with self.assertRaises(ValueError): validate_session(self.session)
        self.setUp();self.session['records'][0]['summary']='Changed text'
        with self.assertRaises(ValueError): validate_session(self.session)

    def test_incomplete_export_requires_explicit_exclusion(self):
        policy=json.loads(TAXONOMY.read_text())
        bills=[{'state':'CA','session_id':'TEST','bill_number':number,'title':'Housing'} for number in ['AB1','AB2']]
        session=initialize(bills,policy)
        annotate(session,session['records'][0]['id'],'assigned',['housing'],{'housing':'Housing'},'Housing law.','test')
        with self.assertRaises(ValueError): export_reference(session)
        result=export_reference(session,True)
        self.assertEqual(result['scored_count'],1)
        self.assertEqual(result['total_input_count'],2)
        self.assertEqual(result['excluded_records'][0]['outcome'],'pending')


if __name__=='__main__': unittest.main()
