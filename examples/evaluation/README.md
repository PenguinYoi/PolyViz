# Real-bill exploratory baseline

Collected November 18, 2026 from the six LegiScan pages linked in `real_bills.json`. Titles and summaries were manually transcribed from the public pages, not downloaded through the API. The records use the user-supplied input format, so the classifier reports `user_supplied` provenance; URLs identify the actual source. This exercise does not validate the LegiScan API adapter.

The California enactment dates follow explicit chaptering and governor-approval entries on those pages. Texas records remain `unknown` here because a displayed Passed status and effective-date action alone were not used to infer enactment. These six bills are for topic evaluation, not production map totals. Session keys are manually assigned labels, not provider numeric IDs. Two California records were enacted in 2026 despite belonging to the 2025–2026 session.

Expected labels are provisional author-assisted judgments from the same title/summary information, not independent expert or full-text annotations. SB79's transportation label is a taxonomy judgment about transit-oriented housing; whether such secondary topics should count needs a consistent policy. This convenience sample was chosen to probe recognizable topics and vocabulary gaps. It is small, limited to two states, not representative, and not a held-out accuracy benchmark.

## Reproduce

```bash
python3 -m polyviz.classifier examples/evaluation/real_bills.json --output data/generated/real_bills.json
python3 -m polyviz.evaluate examples/evaluation/real_bills.json examples/evaluation/review_labels.json --output examples/evaluation/baseline_report.json
```

The version 1 rules exactly match 4 of 6 provisional label sets and recover 6 of 8 expected topic assignments (75% recall). All six predicted topic assignments agree with these review labels; this does not imply 100% precision on other bills.

- CA SB79: housing matched; transportation missed because `transit-oriented` is not a rule.
- TX HB2: education matched.
- TX SB25: healthcare and education matched.
- CA AB288: labor matched.
- CA AB2025: housing missed because `tenancy` is absent from the rules.
- CA AB2020: housing matched.

Rules were deliberately left unchanged to preserve the baseline. Next: have a human review the expected labels, agree on secondary-topic rules, then expand to a more varied sample including out-of-taxonomy and ambiguous bills. If rules are tuned on this sample, evaluate the revised version on new bills.

## Free local semantic comparison

The local MiniLM embedding classifier was run on these same six bills at a provisional cosine threshold of 0.40. Results are saved in `semantic_report.json`:

| Method | Exact label sets | Correct label assignments | Extra labels | Missed labels |
|---|---:|---:|---:|---:|
| Keywords | 4/6 | 6 | 0 | 2 |
| Local embeddings | 2/6 | 7 | 4 | 1 |

Semantic precision was 63.6%, recall 87.5%, and F1 73.7% against provisional review labels. It found housing for AB2025 and transportation for SB79, but produced erroneous taxation candidates on several bills, an education candidate for AB2020, and missed education for SB25. General legal language and broadly related concepts can create false similarities. The initial semantic threshold was not tuned to these results. This is evidence to retain human review and the keyword baseline, not a claim that embeddings improve overall accuracy. See `docs/CLASSIFICATION.md` for the larger evaluation plan.


## Refined local hybrid

The implemented hybrid requires local NLI support plus keyword or embedding corroboration. It matches all 6/6 original development bills (8/8 expected labels, no extras). Those examples informed the changes and are not held-out evidence.

On the six additional real bills in `additional_real_bills.json`, it matched 5/6 complete label sets, recovering 9/10 expected labels with no extra labels. CA SB54's environmental label was missed. The titles/summaries and source URLs were collected November 18, 2026 from the linked LegiScan pages. SB350's long citation-heavy summary was abbreviated to its subject clause; all statuses in this topic-only sample remain unknown. Expected labels were written before running the final hybrid on this sample; no changes were made to fit those results. These are provisional author-assisted judgments, not expert annotations, and the sample is small and non-random.

On 12 synthetic diagnostics the hybrid matched 11/12 label sets. It incorrectly included taxation for a housing example explicitly stating that tax provisions were not changed. These cases are diagnostic fixtures, not real legislation or an independent benchmark.

Saved reports: `hybrid_report.json`, `hybrid_additional_report.json`, `hybrid_diagnostic_report.json`. Reproduce additional-real evaluation with:

```bash
HF_HUB_OFFLINE=1 .venv/bin/python -m polyviz.classifier examples/evaluation/additional_real_bills.json --method hybrid --output data/generated/hybrid_additional.json
.venv/bin/python -m polyviz.evaluate examples/evaluation/additional_real_bills.json examples/evaluation/additional_real_labels.json --predictions data/generated/hybrid_additional.json --output data/generated/hybrid_additional_report.json
```

Model hypotheses were shortened after an initial unsuccessful NLI experiment; the NLI threshold stayed at 0.70. Later clause-level scoring and corroboration were developed on the original six real bills. Keep all reported improvements framed as exploratory. See `docs/CLASSIFICATION.md` for setup and limitations.
