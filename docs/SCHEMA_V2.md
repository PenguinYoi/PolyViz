# Bill schema version 2

Bill IDs are unchanged. New classifier documents use schema version 2 with:

| Field | Meaning |
| --- | --- |
| `policy_topics` | Direct policy topics selected by the existing classification method; not verified facts |
| `topics` | Compatibility alias equal to `policy_topics`, retained for existing evaluators |
| `issue_tags` | Assigned specific issues, initially empty |
| `affected_sectors` | Assigned explicitly affected sectors, initially empty |
| `policy_actions` | Assigned operative changes, initially empty |
| `dates` | Nullable ISO dates: `introduced`, `enacted`, `effective` |
| `issue_classification` | Advisory candidates with exact excerpts, offsets, input/taxonomy hashes and review status |

Assigned arrays and candidates are deliberately separate. Empty assigned issue,
sector, or action arrays mean unresolved, not that these attributes are absent.
Existing topic predictions still need evaluation. A data-center reference does
not automatically establish technology policy or artificial-intelligence content.

## Controlled definitions

`data/topics-v2.json` contains 16 policy topics: the original ten plus business and
economic development, government operations/public finance, technology/digital
policy, land use/development, agriculture/food, and social services. Definitions
include inclusion and exclusion examples. IDs are stable machine identifiers;
display names can change independently. This is an expanded starter vocabulary,
not exhaustive coverage of legislation (civil law, immigration and other domains
may still need additions).

`data/issue-taxonomy.json` separately defines issue, sector and action IDs. Issue
tags are a controlled phrase list. It includes data centers, water use, artificial
intelligence, electricity rates, and tax incentives, plus other specific subjects
such as mental health, Medicaid, and property tax. A tag's `related` phrases are
used only to look up that issue. They are not assignments. Actions cover reporting
obligations, creation of tax incentives, and development restrictions. A phrase
match is a candidate, not a reviewed legal finding.

The classifier defaults to the new topic taxonomy. Original `data/topics.json`
and the frozen historical benchmark remain unchanged. Old results must be reproduced
with `--taxonomy data/topics.json`; scores for the old ten-topic task do not establish
accuracy for the expanded task. The draft annotation policy remains a historical draft.

## Commands

```sh
# Fictional input demonstrates schema and candidate evidence without model downloads.
.venv/bin/python -m polyviz.classifier examples/schema-v2/data-center-input.json --output data/generated/schema-v2-demo.json

# Migrate a saved document without inference or replacing its labels.
.venv/bin/python -m polyviz.schema data/generated/large_hybrid.json --output data/generated/large_hybrid_schema_v2.json
```

Migration copies topics into `policy_topics`, preserves IDs and other metadata,
adds empty new axes and nullable dates, and refuses conflicting old/new labels or
dates. It does not reclassify existing bills or imply their taxonomy is version 2.
New raw user inputs accept `introduced_date`, `enacted_date`, `effective_date`.
LegiScan dates are not inferred from status or arbitrary history events. Multiple
operative effective dates may require a future provision-level date model.

## Identification approach and validation plan

Implemented now: controlled labels, explicit category boundaries, multi-label topics,
separate policy/issue/sector/action axes, exact lexical candidate evidence, provenance,
and unresolved states. Alias matching is only candidate retrieval; it does not resolve
negation, repeal, citations or legal effect. Inclusion/exclusion definitions guide
annotation; the current keyword and model paths do not enforce every definition.
No accuracy gain is claimed for this schema or these new labels.

Recommended next experiment, not implemented training: retrieve candidate labels with
aliases plus existing local embeddings, then score each candidate against operative
clauses with a local semantic model and explicit boundary examples. Keep the full
context for exceptions and negation; use candidates for retrieval, not final decisions.
Evaluate labels on held-out multi-state examples mapped to these definitions. Include
hard negatives such as repealed duties, sector-only tax provisions and ceremonial
measures. Compare with the baseline; tune label-specific thresholds only when label
support is adequate, using validation data separate from training and final testing.
Report per-label precision/recall and unresolved coverage. Cross-state splits should
expose transfer failures, and repeated or companion bill text must not leak across
splits. Published source codes are useful references, but not complete multi-label
policy/sector/action truth.

See scikit-learn's [threshold guidance](https://scikit-learn.org/stable/modules/classification_threshold.html)
for separating fitting and threshold selection. All proposed inference remains local;
no paid API is required.
