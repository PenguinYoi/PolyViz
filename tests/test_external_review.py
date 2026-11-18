import csv
from pathlib import Path
import tempfile
import unittest
from polyviz.external_review import chronological_split,decision,fingerprint,read_source


class ExternalReviewTests(unittest.TestCase):
    def test_numeric_duplicates_do_not_cross_temporal_splits(self):
        records=[{'source_id':'a','session_start':2009,'text':'Provides $100 for schools.','native_topic':'6'},
                 {'source_id':'b','session_start':2013,'text':'Provides $200 for schools.','native_topic':'6'},
                 {'source_id':'c','session_start':2011,'text':'Regulates medical clinics.','native_topic':'3'},
                 {'source_id':'d','session_start':2015,'text':'Changes road safety.','native_topic':'10'}]
        train,cal,test,counts=chronological_split(records)
        self.assertEqual(len(train),1);self.assertEqual(len(cal),1);self.assertEqual(len(test),1)
        self.assertEqual(counts['duplicate_descriptions_removed'],1)
        self.assertFalse({fingerprint(r['text']) for r in train}&{fingerprint(r['text']) for r in test})

    def test_conflicting_reference_groups_are_excluded(self):
        records=[{'source_id':str(i),'session_start':year,'text':text,'native_topic':topic}
                 for i,(year,text,topic) in enumerate([(2009,'School rules','6'),(2011,'Hospital rules','3'),
                   (2015,'Road rules','10'),(2009,'Same statement','3'),(2015,'Same statement','6')])]
        train,cal,test,counts=chronological_split(records)
        self.assertEqual(counts['conflicting_label_group_rows_excluded'],2)
        self.assertEqual(len(train)+len(cal)+len(test),3)

    def test_agreement_does_not_become_verified(self):
        candidates=[{'native_topic':'3','score':0.9},{'native_topic':'6','score':0.05}]
        review=decision(candidates,['healthcare'],'CA')
        self.assertEqual(review['status'],'broad_topic_agreement')
        self.assertEqual(review['verification_status'],'polyviz_labels_not_verified')
        self.assertTrue(review['cross_state_transfer'])
        self.assertEqual(decision(candidates,['housing'],'PA')['status'],'possible_topic_disagreement')
        self.assertEqual(decision(candidates,[],'PA',{'native_topic':'6'})['status'],'external_native_label_available')

    def test_uncertainty_and_unmapped_categories(self):
        self.assertEqual(decision([{'native_topic':'3','score':0.55},{'native_topic':'6','score':0.4}],[],'PA')['status'],'uncertain')
        self.assertEqual(decision([{'native_topic':'20','score':0.9},{'native_topic':'6','score':0.05}],[],'PA')['status'],'native_category_has_no_simple_crosswalk')

    def test_stable_calibration_is_finite_and_monotone(self):
        import numpy as np
        from polyviz.external_review import fit_sigmoids,calibrated_probabilities
        scores=np.array([[3.,-3.],[2.,-2.],[-2.,2.],[-3.,3.]])
        parameters=fit_sigmoids(scores,['a','a','b','b'],['a','b'])
        probabilities=calibrated_probabilities(scores,parameters)
        self.assertTrue(np.isfinite(probabilities).all())
        self.assertTrue(np.allclose(probabilities.sum(axis=1),1))
        self.assertGreater(probabilities[0,0],probabilities[3,0])
        with self.assertRaises(ValueError): calibrated_probabilities(scores,[[1,0]])

    def test_source_parser_keeps_labels_and_excludes_resolutions(self):
        fields=['bill_id','bill_no','year','nuc','majortopic','subtopic','subtype','commemorative','source']
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source.csv'
            with path.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
                writer.writerow(dict(zip(fields,['20150HB0001','HB 1','2015','Changes school funding rules.','6','602','B','0','#https://example.org/bill#'])))
                writer.writerow(dict(zip(fields,['20150HR0001','HR 1','2015','Recognizes a local official.','20','2030','R','1',''])))
            records,excluded=read_source(path)
            self.assertEqual(records[0]['id'],'PA-2015-2016-REGULAR-HB1')
            self.assertEqual(records[0]['native_topic'],'6')
            self.assertEqual(records[0]['native_subtopic'],'602')
            self.assertEqual(excluded['not_eligible_bill'],1)


if __name__=='__main__': unittest.main()
