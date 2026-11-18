"""Local multi-label natural-language-inference classifier; no hosted inference."""
import hashlib
import json
import math
import os
import re
from .semantic import CACHE

MODEL = 'MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33'


def prepare_passages(title, summary):
    """Keep title context and remove only recognizable citation preambles."""
    parts = [title.strip()]
    if summary.strip() and summary.strip() != title.strip():
        # California summaries often say 'An act to amend [citations], relating to X'.
        # Drop the citation only if that explicit subject marker exists.
        if re.match(r'^An act to\b', summary, re.I):
            match = re.search(r'\brelating to\s+(.+)', summary, re.I | re.S)
            if match:
                summary = match.group(1)
        parts.append(summary.strip())
    text = '\n'.join(parts)
    # Token-based windows are applied later; never silently truncate long input.
    return text


def select_topics(rows, threshold):
    return [row for row in rows if row['entailment_score'] >= threshold]


class NLIClassifier:
    def __init__(self, taxonomy, threshold=0.7, allow_download=False, scorer=None):
        if not math.isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError('Threshold must be greater than 0 and at most 1.')
        self.taxonomy, self.threshold = taxonomy, threshold
        self.hypotheses = [(t['id'], t['hypothesis']) for t in taxonomy['topics']]
        self.revision = None
        if scorer is not None:
            self.scorer = scorer
            return
        os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
        os.environ.setdefault('HF_HOME', str(CACHE / 'hf'))
        os.environ.setdefault('TORCH_HOME', str(CACHE / 'torch'))
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
        except ImportError:
            raise ValueError('Install local dependencies: .venv/bin/python -m pip install -r requirements-semantic.txt') from None
        try:
            opts = dict(cache_dir=str(CACHE / 'nli'), local_files_only=not allow_download,
                        trust_remote_code=False)
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL, **opts)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                MODEL, use_safetensors=True, **opts).float().eval()
        except Exception as exc:
            raise ValueError('Could not load local NLI model; first run needs --download-model and internet access. Check installed dependencies.') from exc
        self.torch = torch
        labels = {str(v).lower():int(k) for k,v in self.model.config.id2label.items()}
        entailment = [i for name,i in labels.items() if name.startswith('entail')]
        if len(entailment) != 1 or self.model.config.num_labels != 2:
            raise ValueError('Expected a binary entailment/not-entailment model.')
        self.entailment_id = entailment[0]
        self.revision = getattr(self.model.config, '_commit_hash', None)
        self.scorer = self.score

    def score(self, text, hypotheses):
        tokenizer, torch = self.tokenizer, self.torch
        tokens = tokenizer.encode(text, add_special_tokens=False)
        longest = max(len(tokenizer.encode(h, add_special_tokens=False)) for h in hypotheses)
        budget = min(512, self.model.config.max_position_embeddings) - longest - 8
        if budget < 32:
            raise ValueError('Topic hypothesis is too long for the model.')
        windows = [tokens[i:i+budget] for i in range(0,len(tokens),budget-32)]
        premises = [tokenizer.decode(window, skip_special_tokens=True) for window in windows]
        # Also inspect clauses so a long multi-topic description does not drown
        # out a shorter provision. Full windows remain to preserve context.
        for clause in re.split(r'[\n;,]|(?<=[.!?])\s+', text):
            if 4 <= len(clause.split()) <= 60 and clause.strip() not in premises:
                premises.append(clause.strip())
        pairs = [(passage,h) for passage in premises for h in hypotheses]
        results = []
        for start in range(0,len(pairs),8):
            batch = pairs[start:start+8]
            inputs = tokenizer([p for p,h in batch], [h for p,h in batch],
                               padding=True, truncation=False, return_tensors='pt')
            with torch.inference_mode():
                probabilities = self.model(**inputs).logits.softmax(dim=-1)[:,self.entailment_id].tolist()
            results.extend(probabilities)
        best = []
        for index in range(len(hypotheses)):
            candidates = [(results[w*len(hypotheses)+index],premise) for w,premise in enumerate(premises)]
            best.append(max(candidates, key=lambda item:item[0]))
        return best

    def classify(self, title, summary):
        text = prepare_passages(title, summary)
        scored = self.scorer(text, [hypothesis for _,hypothesis in self.hypotheses])
        if len(scored) != len(self.hypotheses):
            raise ValueError('NLI scorer returned an unexpected number of topic scores.')
        rows = []
        for (topic,hypothesis),(score,passage) in zip(self.hypotheses,scored):
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError('NLI scorer returned an invalid score.')
            rows.append({'topic':topic, 'entailment_score':score,
                         'hypothesis':hypothesis, 'model_input_passage':passage})
        rows.sort(key=lambda row:row['entailment_score'],reverse=True)
        selected = select_topics(rows,self.threshold)
        # Select before rounding so stored display precision does not alter decisions.
        def rounded(row): return {**row,'entailment_score':round(row['entailment_score'],6)}
        return {'topics':[row['topic'] for row in selected],
                'topic_assignments':[rounded(row) for row in selected],
                'classification': {
                    'method':'local_nli', 'method_version':'2', 'model':MODEL,
                    'model_revision':self.revision, 'threshold':self.threshold,
                    'taxonomy_version':self.taxonomy['version'],
                    'hypothesis_version':self.taxonomy['hypothesis_version'],
                    'hypothesis_hash':hashlib.sha256(json.dumps(self.hypotheses).encode()).hexdigest(),
                    'outcome':'candidates_found' if selected else 'unclassified',
                    'review_status':'needs_review',
                    'candidate_scores':[rounded(row) for row in rows],
                    'note':'Entailment scores are not calibrated legislative confidence. Passages show model input, not verified evidence. Review incidental mentions, negation, and unsupported labels.'}}
