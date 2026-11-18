import json
import unittest
from polyviz.classifier import TAXONOMY
from polyviz.nli import NLIClassifier, prepare_passages


class NLITests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = json.loads(TAXONOMY.read_text())
        self.taxonomy['topics'] = self.taxonomy['topics'][:2]

    def test_multiple_labels_without_competing_softmax(self):
        scorer = lambda text,hypotheses: [(0.9,text), (0.85,text)]
        result = NLIClassifier(self.taxonomy,scorer=scorer).classify('Housing and medical services.', '')
        self.assertEqual(result['topics'], ['housing','healthcare'])
        self.assertEqual(result['classification']['review_status'],'needs_review')

    def test_abstains_when_no_label_is_supported(self):
        scorer = lambda text,hypotheses: [(0.1,text), (0.2,text)]
        result = NLIClassifier(self.taxonomy,scorer=scorer).classify('Renames a bridge.', '')
        self.assertEqual(result['topics'],[])
        self.assertEqual(result['classification']['outcome'],'unclassified')

    def test_selection_before_rounding(self):
        scorer = lambda text,hypotheses: [(0.6999999,text), (0.8,text)]
        result = NLIClassifier(self.taxonomy,scorer=scorer).classify('An act.', '')
        self.assertEqual(result['topics'],['healthcare'])

    def test_citation_preamble_removed_without_losing_subject(self):
        text = prepare_passages('Housing programs.', 'An act to amend Section 10 of the Health and Safety Code, relating to housing.')
        self.assertNotIn('Health and Safety Code',text)
        self.assertIn('housing',text)
        self.assertEqual(prepare_passages('Title', 'Amends the Health Code.'),'Title\nAmends the Health Code.')

    def test_invalid_threshold_and_model_scores(self):
        for cutoff in [-1,0,1.1,float('nan')]:
            with self.assertRaises(ValueError):
                NLIClassifier(self.taxonomy,threshold=cutoff,scorer=lambda a,b: [])
        for scores in [[(float('nan'),'x'),(0.8,'x')],[(1.2,'x'),(0.8,'x')],[]]:
            with self.assertRaises(ValueError):
                NLIClassifier(self.taxonomy,scorer=lambda a,b: scores).classify('Title','')


if __name__ == '__main__': unittest.main()
