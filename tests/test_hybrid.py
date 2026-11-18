import json
import unittest
from polyviz.classifier import TAXONOMY
from polyviz.hybrid import HybridClassifier


class Stub:
    def __init__(self,result): self.result=result
    def classify(self,title,summary): return self.result


class HybridTests(unittest.TestCase):
    def test_corroboration_and_flagged_labels(self):
        taxonomy=json.loads(TAXONOMY.read_text())
        nli=Stub({'topics':['housing','labor','healthcare'],
                  'topic_assignments':[{'topic':topic,'entailment_score':0.9} for topic in ['housing','labor','healthcare']],
                  'classification':{'method':'local_nli'}})
        semantic=Stub({'topics':['healthcare'],'classification':{}})
        result=HybridClassifier(taxonomy,nli=nli,semantic=semantic).classify('Housing assistance','An act to help residents.')
        self.assertEqual(result['topics'],['housing','healthcare'])
        self.assertEqual(result['classification']['flagged_assignments'][0]['topic'],'labor')
        self.assertEqual(result['topic_assignments'][0]['corroboration'],['keyword_in_cleaned_text'])
        self.assertEqual(result['topic_assignments'][1]['corroboration'],['embedding_similarity'])

    def test_keywords_cannot_create_labels_without_nli_support(self):
        taxonomy=json.loads(TAXONOMY.read_text())
        result=HybridClassifier(taxonomy,
          nli=Stub({'topics':[],'topic_assignments':[],'classification':{}}),
          semantic=Stub({'topics':['housing'],'classification':{}})).classify('Housing','')
        self.assertEqual(result['topics'],[])


if __name__ == '__main__': unittest.main()
