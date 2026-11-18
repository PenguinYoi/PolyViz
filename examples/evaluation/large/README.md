# Larger real-bill evaluation

Start with [REPORT.md](REPORT.md). This evaluates frozen models against provisional assistant-assigned labels, not independent human ground truth.

## Files

- `selection.json`: original seeded selections, listing-page sampling frames, and eight retrieval exclusions.
- `bills.json`: 52 real bill titles and summaries with source URLs, excluding the prior 12 real evaluation bills.
- `review_labels.json`: reference topic sets, rationales, and 21 uncertainty flags, assigned before inference.
- `frozen_snapshot.json`: SHA-256 hashes of classifier files, taxonomy, inputs, and labels before the run.
- `keyword_report.json`, `semantic_report.json`, `hybrid_report.json`: overall, per-topic, per-state, and subset metrics plus individual disagreements.
- `blind_review.json`: independent labeling worksheet without model predictions or proposed labels. `topics: null` means not yet reviewed; `topics: []` means reviewed without a supported topic. `needs_more_text` distinguishes insufficient text.
- `review_queue.json`: hybrid/reference disagreements, including model suggestions flagged for review. These are not automatically confirmed mistakes.

All three methods ran locally with no paid APIs or credits. Models and thresholds were not changed during this evaluation. The evaluation utility was expanded to report richer metrics. Sample bill statuses intentionally remain unknown: this dataset must not feed enacted-law map totals.

## Sampling

For CA, TX, FL, NY, IL, and WA, inspect the first `legislation/2025` page. Keep bill identifiers (AB/HB/SB/A/S/H plus digits), exclude resolutions and previous evaluation bills, sort by identifier as recorded in the frame, and shuffle with seed `20261118 + first_state_character_code * 100 + second_state_character_code`. Each shuffle step updates the unsigned 32-bit state with `1664525 * state + 1013904223`, using modulo `i+1` for its swap index. Select ten per state.

Public web lookup retrieved complete detail-page titles and summaries for 52/60 selections. Direct HTTP collection returned 403; it was not used or bypassed. Eight unavailable pages were excluded before labeling/inference, with no truncated listing substituted. Live listing pages can change; the frozen selection and dataset—not a future live recollection—define this evaluation. Retrieval exclusions can bias the sample.

The resulting sample is a recent-listing convenience sample, not nationally representative. It includes mixed legislative statuses and many Florida local-district bills. Nine topics have expected positive labels; energy has none. Two bills with similar substantive text remain distinct legislative records. Provisional secondary-topic decisions require human adjudication.

## Reproduce

Run from the repository root with the free models already cached:

```bash
.venv/bin/python -m polyviz.classifier examples/evaluation/large/bills.json --output data/generated/large_keywords.json
HF_HUB_OFFLINE=1 .venv/bin/python -m polyviz.classifier examples/evaluation/large/bills.json --method semantic --output data/generated/large_semantic.json
HF_HUB_OFFLINE=1 .venv/bin/python -m polyviz.classifier examples/evaluation/large/bills.json --method hybrid --output data/generated/large_hybrid.json
```

Evaluate each output against the same frozen reference:

```bash
.venv/bin/python -m polyviz.evaluate examples/evaluation/large/bills.json examples/evaluation/large/review_labels.json --predictions data/generated/large_keywords.json --output data/generated/large_keyword_report.json
.venv/bin/python -m polyviz.evaluate examples/evaluation/large/bills.json examples/evaluation/large/review_labels.json --predictions data/generated/large_semantic.json --output data/generated/large_semantic_report.json
.venv/bin/python -m polyviz.evaluate examples/evaluation/large/bills.json examples/evaluation/large/review_labels.json --predictions data/generated/large_hybrid.json --output data/generated/large_hybrid_report.json
```

For installation and first-time free model downloads, see [CLASSIFICATION.md](../../../docs/CLASSIFICATION.md).

## Human annotation rules

1. Read only the supplied title/summary and topic definitions before assigning labels; if checking full text, record that separately because it changes the task.
2. Assign all substantively addressed topics, including secondary topics when an actual provision changes that policy area.
3. Do not label a topic solely from a code citation, an affected occupation, or a passing reference. Industrial zoning does not automatically mean housing; a school tax is not automatically education policy.
4. Record insufficient information separately from a clearly outside-taxonomy subject. A generic budget does not reveal every funded topic.
5. Flag disputed boundaries: civil versus criminal justice, pensions as labor, public-health district governance, and sector-specific tax policy.
6. Complete independent annotations before examining predictions, then adjudicate disagreements with the provisional reference. Preserve the original reference and write a new version.

A human-reviewed sample and clearer category boundaries are needed before reporting trustworthy classifier accuracy or publishing automatically categorized map totals.
