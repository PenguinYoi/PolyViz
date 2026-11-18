# Local semantic classification

PolyViz offers two classifiers: the original offline keyword baseline and an optional local sentence-embedding model. Neither uses paid APIs, hosted inference, API keys, or credits. The embedding model requires a free initial download and local CPU, disk, and memory resources. Bill text is processed on your computer, not sent to a model service.

## Setup and run

Python 3.10+ is recommended for the optional semantic dependencies; the development environment currently uses Python 3.9. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-semantic.txt
python -m polyviz.classifier examples/evaluation/real_bills.json --method semantic --download-model --output data/generated/semantic.json
```

The explicit `--download-model` flag permits model-file retrieval from Hugging Face. No account or access token is needed for this public model. Subsequent runs default to cached files only:

```bash
python -m polyviz.classifier examples/evaluation/real_bills.json --method semantic --output data/generated/semantic.json
python -m polyviz.evaluate examples/evaluation/real_bills.json examples/evaluation/review_labels.json --predictions data/generated/semantic.json --output data/generated/semantic_report.json
```

Compare with the keyword baseline using the same inputs and labels:

```bash
python -m polyviz.classifier examples/evaluation/real_bills.json --output data/generated/keywords.json
python -m polyviz.evaluate examples/evaluation/real_bills.json examples/evaluation/review_labels.json --predictions data/generated/keywords.json --output data/generated/keyword_report.json
```

Model cache and generated data are ignored by Git. Set `HF_HUB_OFFLINE=1` for an additional offline setting after the download. This is model inference on the local machine, not a vector database or cloud endpoint.

## How it works

1. Embed each topic definition and its illustrative semantic examples from `data/topics.json`.
2. Split title and summary into short passages, embedding each locally.
3. Compute cosine similarity between each passage and topic reference.
4. Keep the highest score per topic, allowing every topic above the cutoff.
5. Save all scores, selected topics, the matched passage and reference, model identifier, reference hash, and threshold for inspection.

Uses `sentence-transformers/all-MiniLM-L6-v2`, a general-purpose English embedding model. It is not specifically trained to interpret legislation. See the [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [Sentence Transformers similarity documentation](https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html).

The default threshold of 0.40 is an experimental starting point, not a validated accuracy guarantee or probability. Adjust with `--threshold 0.45`, for example. Do not tune solely on the six demonstration bills and report that as held-out performance. Scores are recorded before rounding-based display; classification uses the original score.

## Topic assignment policy for human review

Assign multiple topics when distinct substantive provisions address them. Do not assign a topic solely because a bill mentions a legal code, institution, or population. A mental-health bill that also changes school resources or duties may address healthcare and education; a mention of students alone does not establish this. Transit-oriented housing does not automatically change transportation policy: secondary-topic decisions require a documented inclusion rule and enough text.

Embeddings do NOT reliably enforce these distinctions or reason about negation. A matched passage is a similarity explanation, not proof of substantive relevance. Every semantic result is marked `needs_review`; no primary/secondary role or probability is fabricated. An unmatched bill stays unclassified rather than being declared outside the taxonomy. Vague text may require a longer description or full-text review.

## Evaluation plan

The six real bills are an exploratory convenience sample with provisional labels. Review those labels, especially secondary-topic judgments, before treating them as a reference. Next, independently label a larger sample across topics, states, ambiguous cases, and subjects outside this taxonomy. Use a development subset for threshold/reference tuning and reserve a separate evaluation subset. Report exact label-set matches, missed labels, extra labels, precision, recall, and F1. Do not equate unit-test success with semantic accuracy.

Keyword terms remain unchanged to preserve the baseline. Semantic reference text is separately versioned, with a hash stored in output. Re-run comparisons after any definition, reference, threshold, or model change.

## Initial run

The free model successfully processed the six real demonstration bills. At the initial 0.40 threshold it recovered 7/8 expected labels but added four incorrect labels, compared with 6/8 and no extra labels for keywords. Only 2/6 semantic label sets exactly matched, compared with 4/6 for keywords. Results and limitations are recorded in `examples/evaluation/semantic_report.json` and its README. A cached offline run was also checked. This is a working experimental alternative, not a replacement approved for map production.

## Refined option: local natural-language inference (NLI)

Embedding similarity asks whether text resembles a topic. NLI instead scores whether the text supports an explicit topic statement. PolyViz now offers `--method nli` with the free `MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33` model. It runs entirely locally and scores each topic independently, so one supported topic does not suppress another. No API credentials or billing are involved. See the [model card](https://huggingface.co/MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33) and [research paper](https://arxiv.org/abs/2312.17543).

```bash
.venv/bin/python -m pip install -r requirements-semantic.txt
.venv/bin/python -m polyviz.classifier examples/evaluation/real_bills.json --method nli --download-model --output data/generated/nli.json
.venv/bin/python -m polyviz.evaluate examples/evaluation/real_bills.json examples/evaluation/review_labels.json --predictions data/generated/nli.json --output data/generated/nli_report.json
```

After the free download, omit `--download-model` and optionally set `HF_HUB_OFFLINE=1`. Keyword and embedding methods remain available for comparison. The CLI default stays keywords to preserve existing behavior; NLI is explicitly selected.

### Refinements

- Topic statements live in `data/topics.json` as `hypothesis`, separately versioned from keyword and embedding references.
- Scores use a binary entailment/not-entailment decision independently for every topic, rather than a softmax competition across topics.
- Recognizable `An act to ... relating to ...` citation preambles are stripped from summaries to reduce legal-code distractions. Original title and summary stay in the JSON unchanged.
- Long input is evaluated with overlapping token windows; it is not silently truncated. Output retains the highest-scoring model-input window for each topic.
- The NLI threshold is 0.70, selected before the initial run and retained through refinement. Long topic statements initially abstained on all six development bills; short topic statements (hypothesis version 2) and clause scoring replaced them after inspecting development results. `--threshold` can override it. It is experimental, not calibrated confidence.
- Every result remains marked for human review. Model-input passages are not presented as verified supporting quotations. The classifier does not invent a primary/secondary distinction or force any topic.

NLI is still fallible on negation, incidental mentions, insufficient descriptions, and legal nuance. The small model is general purpose, not trained specifically on state legislation. Classification quality depends on the supplied description; a vague summary cannot establish every provision of a bill.

`diagnostic_bills.json` and `diagnostic_labels.json` contain twelve explicitly synthetic cases authored before the first NLI run. They probe overlapping topics, negation, generic legal language, and abstention. They do not establish performance on real unseen bills. The original six real bills are development examples, not held-out validation. Keep their existing provisional labels visible rather than changing them to make model scores look better.


## Experimental method: hybrid

```bash
HF_HUB_OFFLINE=1 .venv/bin/python -m polyviz.classifier examples/evaluation/real_bills.json --method hybrid --output data/generated/hybrid.json
```

On a fresh machine, install `requirements-semantic.txt`, omit `HF_HUB_OFFLINE=1`, and add `--download-model` for the free initial downloads. Both the embedding and NLI models are needed. After caching, this method was tested fully offline.

Hybrid classification requires NLI support at 0.70 plus either an exact keyword in the cleaned text or embedding similarity at 0.40. Keywords cannot assign labels on their own. NLI suggestions without corroboration are retained under `classification.flagged_assignments` for human review, rather than discarded without explanation. Both component thresholds and model metadata are saved. Corroboration is a heuristic, not independent evidence of correctness, and may reduce recall.

Refinement decisions were informed by the original six examples, so improvements on them are development results. The final hybrid matched all six provisional label sets (8 labels, no extras). Twelve synthetic diagnostics matched 11/12 label sets: the failure was an extra taxation label on text explicitly saying tax rates/credits/exemptions were not changed. This exposes an unresolved negation limitation; the result is retained rather than tuning away a diagnostic failure and claiming general accuracy. All results remain `needs_review`.

An additional six-real-bill sample with source URLs and provisional expected labels was created before running the final hybrid on it. It is a small convenience sample, not an independent representative benchmark. No further tuning is performed on its results in this iteration. Secondary-topic judgments remain debatable; reviewers should agree on them before expanding the map.


Additional-real results: 5/6 complete label sets, 9/10 expected labels, no extras. CA SB54's environmental topic was missed. This reinforces the cost of conservative selection: retain the review queue and inspect unclassified bills. Do not treat the small sample's precision as a general accuracy claim.


## Larger frozen evaluation supersedes the small-sample impression

See [the 52-bill report](../examples/evaluation/large/REPORT.md). Hybrid precision/recall were 78.8%/55.3% against provisional assistant labels, with 27/52 exact topic sets. Keywords scored 28/52 and embeddings 21/52. These are exploratory agreement metrics, not human-verified accuracy, and do not show hybrid superiority. Twenty-one cases were premarked ambiguous; energy was not tested. The classifier and taxonomy remained unchanged. Prioritize independent annotation, topic-boundary agreement, better descriptions, and a new untouched test sample over further tuning on these results.


## External-label automated second opinion

The user chose to prioritize existing externally coded legislation over manual labeling. [AUTOMATED_REVIEW.md](AUTOMATED_REVIEW.md) describes the implemented local supervised reviewer, its researcher-coded Pennsylvania source, temporal evaluation, and exact source-label lookup. It does not overwrite custom topic/sector labels or declare them verified. This is the current automated review path; earlier manual review tools are optional.
