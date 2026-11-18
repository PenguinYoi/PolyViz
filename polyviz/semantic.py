"""Free local embedding classifier. Similarity is not a probability or proof."""
import hashlib
import json
import math
import os
import re
from pathlib import Path

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
CACHE = Path(__file__).resolve().parents[1] / 'data' / 'model_cache'


def cosine(left, right):
    denominator = math.sqrt(sum(x*x for x in left) * sum(x*x for x in right))
    return sum(x*y for x,y in zip(left,right)) / denominator if denominator else 0.0


class SemanticClassifier:
    def __init__(self, taxonomy, threshold=0.4, allow_download=False, encoder=None):
        if not 0 < threshold <= 1:
            raise ValueError('Threshold must be greater than 0 and at most 1.')
        self.taxonomy = taxonomy
        self.threshold = threshold
        if encoder is None:
            # Local computation only; no inference endpoints, tokens, or billing.
            os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
            os.environ.setdefault('HF_HOME', str(CACHE / 'hf'))
            os.environ.setdefault('TORCH_HOME', str(CACHE / 'torch'))
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ValueError('Install optional local dependencies: python3 -m pip install -r requirements-semantic.txt') from None
            try:
                encoder = SentenceTransformer(MODEL, cache_folder=str(CACHE),
                                              local_files_only=not allow_download,
                                              trust_remote_code=False, device='cpu')
            except Exception as exc:
                raise ValueError('Could not load local embedding model. First run requires --download-model and internet access; later runs use cached files.') from exc
        self.encoder = encoder
        self.references = []
        for topic in taxonomy['topics']:
            for text in [topic['name'] + ': ' + topic['description']] + topic.get('semantic_examples', []):
                self.references.append((topic['id'], text))
        self.vectors = self.encode([text for _,text in self.references])

    def encode(self, texts):
        return self.encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()

    def classify(self, title, summary):
        # Short chunks avoid silently truncating long summaries. This interface
        # accepts title/summary, not complete legislative documents.
        excerpts = [title] + re.split(r'(?<=[.!?;])\s+', summary)
        chunks = []
        for excerpt in excerpts:
            words = excerpt.split()
            chunks.extend(' '.join(words[i:i+60]) for i in range(0,len(words),60))
        chunks = list(dict.fromkeys(c for c in chunks if c))
        vectors = self.encode(chunks)
        scores = {}
        for (topic, reference), ref_vector in zip(self.references, self.vectors):
            for chunk, vector in zip(chunks, vectors):
                score = cosine(vector, ref_vector)
                if topic not in scores or score > scores[topic]['similarity']:
                    scores[topic] = {'topic':topic, 'similarity':score,
                                     'matched_excerpt':chunk, 'reference':reference}
        ranked = sorted(scores.values(), key=lambda item:item['similarity'], reverse=True)
        assignments = [{**row, 'similarity':round(row['similarity'],6)} for row in ranked
                       if row['similarity'] >= self.threshold]
        return {'topics':[row['topic'] for row in assignments],
                'topic_assignments':assignments,
                'classification': {
                    'method':'local_embeddings', 'method_version':'1', 'model':MODEL,
                    'taxonomy_version':self.taxonomy['version'],
                    'semantic_reference_version':self.taxonomy.get('semantic_version','1'),
                    'reference_hash':hashlib.sha256(json.dumps(self.references).encode()).hexdigest(),
                    'threshold':self.threshold, 'review_status':'needs_review',
                    'outcome':'candidates_found' if assignments else 'unclassified',
                    'candidate_scores':[{**row,'similarity':round(row['similarity'],6)} for row in ranked],
                    'note':'Similarity candidates require human review; scores are not probabilities. No match does not establish outside-taxonomy status.'}}
