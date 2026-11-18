"""Conservative local NLI with independently recorded corroboration signals."""
from .classifier import classify
from .nli import NLIClassifier, prepare_passages
from .semantic import SemanticClassifier


class HybridClassifier:
    def __init__(self, taxonomy, threshold=0.7, allow_download=False,
                 nli=None, semantic=None):
        self.taxonomy = taxonomy
        self.nli = nli or NLIClassifier(taxonomy,threshold,allow_download)
        self.semantic = semantic or SemanticClassifier(taxonomy,0.4,allow_download)

    def classify(self,title,summary):
        result = self.nli.classify(title,summary)
        clean = prepare_passages(title,summary)
        keyword_result = classify('',clean,self.taxonomy)
        embedding_result = self.semantic.classify(title,summary)
        keyword_topics, embedding_topics = set(keyword_result['topics']), set(embedding_result['topics'])
        accepted, flagged = [], []
        for assignment in result['topic_assignments']:
            topic = assignment['topic']
            signals = []
            if topic in keyword_topics: signals.append('keyword_in_cleaned_text')
            if topic in embedding_topics: signals.append('embedding_similarity')
            row = {**assignment,'corroboration':signals}
            (accepted if signals else flagged).append(row)
        result['topics'] = [row['topic'] for row in accepted]
        result['topic_assignments'] = accepted
        result['classification'].update({
            'method':'local_hybrid','method_version':'1',
            'outcome':'candidates_found' if accepted else 'unclassified',
            'flagged_assignments':flagged,
            'keyword_evidence':keyword_result['classification']['evidence'],
            'embedding_classification':embedding_result['classification'],
            'note':'Selected labels require NLI support plus keyword or embedding corroboration. These signals are not independent validation. Flagged NLI labels are retained for review; recall may decrease. All labels still require evaluation.'})
        return result
