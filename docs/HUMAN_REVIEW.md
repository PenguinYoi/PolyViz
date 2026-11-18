# Optional independent annotation workflow

**Update:** an automated reviewer using existing research labels is now available; see [AUTOMATED_REVIEW.md](AUTOMATED_REVIEW.md). The manual workflow below is optional, not a prerequisite for using the project.

The user selected separate **direct policy topics** and **affected sectors**. Read [the category guide](ANNOTATION_GUIDE.md) before labeling. The ten-topic draft policy is in `data/policies/topics-v2-draft.json`; the original taxonomy and frozen evaluation remain unchanged.

A review session with 52 pending records is prepared at `data/reviews/large-v2.json`. It contains original input text and no model predictions, provisional labels, or assistant audit suggestions.

## Start with five bills

From the repository root:

```bash
.venv/bin/python -m polyviz.review run --session data/reviews/large-v2.json --reviewer your-name
```

The command shows one bill at a time and accepts:

- Comma-separated policy topic IDs, such as `housing,taxation`.
- `outside` if the subject is clear but no direct topic fits.
- `more` when more text is needed before deciding.
- `s` to skip a bill for now, or `q` to stop.

For assigned topics, paste an exact supporting excerpt from the displayed title or summary. Add affected-sector IDs separately, with their own excerpts. Empty sector input means reviewed with no tags; `?` leaves that axis unreviewed. Write a brief rationale. Quote checks establish source provenance only; they cannot verify whether your interpretation is correct.

Each valid annotation is saved immediately. Invalid annotations are not saved. The command stops after five saved records by default; repeat it to continue, or use `--limit 10`. Do not open `assistant_audit.json`, previous reference labels, or model predictions until completing independent annotations.

Check progress:

```bash
.venv/bin/python -m polyviz.review status --session data/reviews/large-v2.json
```

Revisit your own annotation using its displayed ID; previous versions remain in its history:

```bash
.venv/bin/python -m polyviz.review run --session data/reviews/large-v2.json --reviewer your-name --record CA-2025-2026-REGULAR-AB1987
```

A second person should initialize a separate session from the same inputs and policy, rather than see or overwrite the first person's labels:

```bash
.venv/bin/python -m polyviz.review init examples/evaluation/large/bills.json --policy data/policies/topics-v2-draft.json --session data/reviews/second-review.json
```

## Export carefully

```bash
.venv/bin/python -m polyviz.review export --session data/reviews/large-v2.json --output data/reviews/large-v2-reference.json
```

Export refuses pending or needs-more-text records. To explicitly export only resolved records, add `--allow-incomplete`. The result reports the full denominator and excluded IDs; unresolved records never silently become empty topic sets. A reviewer name is self-reported provenance, not proof of independent external review.

References store direct topics under `labels` and sector tags under `affected_sectors`. They must be evaluated separately; the current evaluator scores direct topics only. The existing automated classifiers do not yet predict affected sectors as a separate axis.

## Evaluate under the same definitions

Version 2 labels cannot be compared with version 1 predictions as if definitions were unchanged. After the draft policy is accepted and enough labels are resolved, generate a fresh prediction file explicitly using the same policy:

```bash
HF_HUB_OFFLINE=1 .venv/bin/python -m polyviz.classifier examples/evaluation/large/bills.json --taxonomy data/policies/topics-v2-draft.json --method hybrid --output data/generated/large-v2-hybrid.json
.venv/bin/python -m polyviz.evaluate examples/evaluation/large/bills.json data/reviews/large-v2-reference.json --taxonomy data/policies/topics-v2-draft.json --predictions data/generated/large-v2-hybrid.json --require-user-review --output data/generated/large-v2-human-report.json
```

For an explicitly incomplete reference, evaluation also requires `--allow-partial-reference`; reports then show scoring coverage and excluded IDs. Do not report that subset's score without its coverage. `--require-user-review` rejects assistant-draft reference annotations; it checks provenance metadata, not an externally authenticated reviewer identity.

The current models have not been trained or validated against the new policy merely because it exists. Classification results under it remain provisional.

## What happens next

1. Resolve category boundaries, using disagreements between independent reviewers.
2. Seek fuller source descriptions for `needs_more_text` cases. If input text changes, initialize a new input version so comparisons remain traceable.
3. Adjudicate and export reference labels; preserve original annotations and rationales.
4. Treat all already-inspected examples as development material for future model/reference tuning. Do not relabel examples to match a classifier.
5. Evaluate any revised model on a new, untouched set with positive examples for every category, including energy, plus out-of-taxonomy and multi-topic bills.
6. Choose the classifier by measured held-out performance and review burden, not by complexity. No improvement is claimed until it is measured.

No paid API or credits are used by this workflow. Human review requires no model download or inference.
