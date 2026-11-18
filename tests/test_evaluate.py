import unittest
from polyviz.evaluate import evaluate,metrics


class EvaluationTests(unittest.TestCase):
    def test_known_multilabel_metrics_and_subsets(self):
        taxonomy={'version':'1','topics':[{'id':'housing'},{'id':'taxation'},{'id':'energy'}]}
        bills=[{'id':'a','state':'CA','topics':['housing'],'classification':{'method':'test'}},
               {'id':'b','state':'TX','topics':['taxation'],'classification':{'method':'test'}}]
        reference={'labels':{'a':['housing','taxation'],'b':[]},
                   'annotations':{'a':{'ambiguous':False},'b':{'ambiguous':True}}}
        report=evaluate(bills,reference,taxonomy)
        self.assertEqual(report['true_positive_labels'],1)
        self.assertEqual(report['extra_labels'],1)
        self.assertEqual(report['missed_labels'],1)
        self.assertEqual(report['micro_f1'],0.5)
        self.assertEqual(report['per_topic']['energy']['recall'],None)
        self.assertEqual(report['subsets']['clear_reference']['count'],1)
        self.assertEqual(report['subsets']['multiple_expected_topics']['count'],1)
        self.assertEqual(report['per_state']['TX']['extra_labels'],1)

    def test_empty_denominators_are_not_perfect_accuracy(self):
        self.assertIsNone(metrics([])['exact_match_rate'])
        row={'expected':[],'predicted':[],'extra':[],'missing':[],'exact_match':True}
        self.assertEqual(metrics([row])['exact_match_rate'],1)
        self.assertIsNone(metrics([row])['micro_precision'])

    def test_duplicate_ids_and_unknown_topics_rejected(self):
        bill={'id':'a','state':'CA','topics':['housing'],'classification':{'method':'test'}}
        taxonomy={'version':'1','topics':[{'id':'housing'}]}
        with self.assertRaises(ValueError): evaluate([bill,bill],{'labels':{'a':['housing']}},taxonomy)
        with self.assertRaises(ValueError): evaluate([bill],{'labels':{'a':['unknown']}},taxonomy)


if __name__=='__main__': unittest.main()
