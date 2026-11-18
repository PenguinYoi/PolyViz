import json
import unittest
from polyviz.classifier import TAXONOMY
from polyviz.semantic import SemanticClassifier, cosine


class Array:
    def __init__(self, rows): self.rows = rows
    def tolist(self): return self.rows


class FakeEncoder:
    """Deterministic vectors test selection logic, not model accuracy."""
    def encode(self, texts, **kwargs):
        rows = []
        for text in texts:
            lower = text.lower()
            if 'mental health' in lower or 'medical' in lower or lower.startswith('healthcare:'):
                rows.append([0.,1.,0.])
            elif 'housing' in lower or 'tenancy' in lower or 'homes' in lower:
                rows.append([1.,0.,0.])
            else:
                rows.append([0.,0.,1.])
        return Array(rows)


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = json.loads(TAXONOMY.read_text())
        # Two topics make exact behavior of fake vectors explicit.
        self.taxonomy['topics'] = self.taxonomy['topics'][:2]

    def test_multilabel_and_excerpts(self):
        model = SemanticClassifier(self.taxonomy, encoder=FakeEncoder())
        result = model.classify('Housing assistance.', 'Medical care and mental health treatment.')
        self.assertEqual(set(result['topics']), {'housing','healthcare'})
        self.assertEqual(result['classification']['review_status'], 'needs_review')
        for row in result['topic_assignments']:
            self.assertIn(row['matched_excerpt'], ['Housing assistance.', 'Medical care and mental health treatment.'])

    def test_no_forced_label(self):
        model = SemanticClassifier(self.taxonomy, encoder=FakeEncoder())
        self.assertEqual(model.classify('An unrelated subject.', '')['topics'], [])

    def test_threshold_validation(self):
        for cutoff in [-1,0,1.1,float('nan')]:
            with self.assertRaises(ValueError):
                SemanticClassifier(self.taxonomy, threshold=cutoff, encoder=FakeEncoder())

    def test_cosine(self):
        self.assertAlmostEqual(cosine([1,0],[1,0]),1)
        self.assertEqual(cosine([0,0],[1,0]),0)
        self.assertEqual(cosine([1,0],[0,1]),0)


if __name__ == '__main__': unittest.main()
