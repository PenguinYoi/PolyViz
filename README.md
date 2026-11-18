# PolyViz

**Explore what U.S. states are legislating about—by topic, place, and time.**

PolyViz is a planned interactive U.S. map that organizes enacted state legislation into topics such as housing, healthcare, and education. Users will be able to explore geographic patterns, compare legislative activity, and inspect the bills behind the visualization.

## Core question

What topics are state legislatures passing laws about, and how does that vary across states and time?

The initial audience is curious residents and students who want an accessible overview without searching individual legislative databases.

## Planned first version

- Interactive U.S. map with a consistent color scale and visible legend.
- Topic and enactment-year filters.
- Toggle between enacted bill counts and each topic's share of enacted bills.
- State hover tooltips with key figures.
- Clickable state panels with topic breakdowns, bill summaries, and source links.
- State search and clear coverage notes.

Start with one completed year and a limited, documented set of topics. Validate a small selection of states before expanding to all 50. State comparisons, historical animation, and an optional 3D view are later enhancements.

## Data approach

Collect legislative records from a selected provider, preserve the originals, normalize one record per bill, assign consistent topic labels, and validate the results. Store canonical records as JSON grouped by state and session. Generate separate aggregate JSON files for the map.

The first version is intended to be a static website reading prepared data files. Data collection and classification happen before publication, rather than while a visitor browses the map. The data provider, frontend stack, and hosting provider have not yet been selected.

## Interpretation

- “Passed” means enacted into law, rather than passed by a single chamber.
- Bill counts describe legislative activity, not policy effectiveness, public opinion, or the importance of a law.
- Bills may have multiple topics, so topic shares can sum to more than 100%.
- Missing coverage must be distinguishable from zero activity.
- Community-needs comparisons are a possible future research extension, outside the initial scope.

## Project status

Planning stage. No application, production dataset, or hosting deployment has been implemented yet.

See [the workflow plan](docs/WORKFLOW.md) for architecture, data conventions, and milestones.

## Run the first classifier

Requires Python 3.9+ and no third-party dependencies. From the repository root:

```bash
python3 -m polyviz.classifier examples/bill.json --output data/generated/example.json
python3 -m unittest discover -s tests -v
```

The example is fictional. You can replace it with your own bill JSON or a saved LegiScan `getBill` response. The command also accepts an array of bill records. It writes a document with `schema_version`, `generated_at`, and a `bills` array. It does not fetch bills, call AI services, or create a database.

For user-supplied records, provide `state`, `session_id`, `bill_number`, and a nonempty `title`; optionally include `summary`, `origin_chamber`, `status`, `enacted_date`, and `source_url`. Status defaults to `unknown`. Include a distinct identity for special sessions. For LegiScan records, the importer uses the provider's session ID. It leaves origin chamber unknown unless explicitly supplied rather than inferring it from the bill's current chamber.

Classification uses title and summary/LegiScan description, not downloaded full text. Edit category definitions and terms in `data/topics.json`. Labels support multiple topics, and output records retain matching terms as evidence. Every matched result is unreviewed; unmatched results are unclassified and need review. There is no calibrated confidence score. This baseline cannot reliably interpret negation, incidental mentions, policy direction, or complex legal language. Do not use its labels for public conclusions before evaluating a manually labeled sample. Keep an input copy because output intentionally omits most provider fields.

LegiScan's numeric status 4 is labeled “Passed” in its API manual. The importer conservatively preserves it as `source_status: 4` and sets normalized status to `unknown`, with a warning, until enactment is verified. It does not derive enactment dates from arbitrary action text. Unknown statuses must not be counted as failed or enacted. See the [LegiScan API manual](https://api.legiscan.com/dl/LegiScan_API_User_Manual.pdf).

Generated output and raw downloads are ignored by Git. This classifier is implemented; the map, national data pipeline, classification evaluation, and deployment remain planned.

## Real-bill pilot

A six-bill, two-state exploratory evaluation is available in [examples/evaluation](examples/evaluation/README.md), including source URLs, provisional review labels, reproduction commands, and the baseline report. It identifies vocabulary gaps without changing the rules and is not a representative accuracy benchmark.

## Free local semantic classifier

An optional embedding-based classifier supports multiple topic candidates without keyword matching or paid APIs. It runs locally and records similarity scores and matching passages for review. See [setup, evaluation commands, and limitations](docs/CLASSIFICATION.md). Model installation and a free initial download are required; semantic accuracy must be evaluated separately from code tests.


## Refined classifier (recommended experiment)

A free local hybrid combines a natural-language-inference model with corroborating embedding/keyword signals. It scores topics independently, supports multiple labels, removes recognizable citation boilerplate for analysis, and retains uncertain suggestions for review. The keyword default is unchanged; select the hybrid explicitly:

```bash
.venv/bin/python -m polyviz.classifier examples/evaluation/real_bills.json --method hybrid --output data/generated/hybrid.json
```

First-time setup on another machine requires optional dependencies and `--download-model`; subsequent runs can be fully offline. See [classification documentation](docs/CLASSIFICATION.md). Exploratory results: 6/6 original development bills and 5/6 additional real bills matched their provisional complete label sets. Negation and missed topics remain known limitations. No paid APIs or credits are used.


## Larger evaluation: current limitations

A frozen 52-bill sample across six states produced complete-topic-set matches of 28/52 for keywords, 21/52 for embeddings, and 27/52 for the hybrid against provisional assistant labels. The hybrid did not outperform keywords on this sample. The earlier six-bill development result does not establish general accuracy. See the [full evaluation report](examples/evaluation/large/REPORT.md) and independent human-labeling worksheet before relying on automated topic totals. No classifier or taxonomy tuning was performed during this evaluation.


## Review labels independently

A blind annotation workflow is prepared for the 52-bill sample. It stores direct policy topics separately from affected sectors, requires supporting excerpts, saves progress in five-bill batches, and distinguishes unresolved records from outside-taxonomy bills. See [the human-review instructions](docs/HUMAN_REVIEW.md) and [draft category definitions](docs/ANNOTATION_GUIDE.md).

```bash
.venv/bin/python -m polyviz.review run --session data/reviews/large-v2.json --reviewer your-name
```

No human annotations have been supplied yet. The version 2 policy remains a draft, and no new accuracy claim is made from assistant revisions. Existing models and frozen version 1 evaluation files are preserved.


## Automated reviewer using external research labels

You can now run a free local reviewer trained on researcher-coded Pennsylvania legislation instead of manually labeling all 52 sample bills. It learns and evaluates the source's primary topics, keeps native source labels separate from custom policy topics and affected sectors, and flags uncertain or conflicting results.

```bash
.venv/bin/python -m polyviz.external_review review data/generated/large_hybrid.json --output data/generated/large_external_review.json
```

The model is trained in this checkout; see [fresh setup, source provenance, and results](docs/AUTOMATED_REVIEW.md). On 3,928 later Pennsylvania bills it achieved 83.2% primary-topic agreement. This is not a claim of 83.2% multi-topic accuracy across all states. Manual review remains optional for adjudicating unresolved cases; no manual session is required to use this reviewer.

The external reviewer also emits advisory contextual topic/sector suggestions.
Original labels stay intact. A separate Florida transfer audit documents limits
of applying the Pennsylvania-trained reviewer across states; see
[automated review](docs/AUTOMATED_REVIEW.md).

New classifier output uses [schema version 2](docs/SCHEMA_V2.md): 16 policy topics,
separate issue/sector/action fields, nullable timeline dates, and advisory issue
candidates with source excerpts. Bill IDs are unchanged. Use `--taxonomy data/topics.json`
when reproducing historical ten-topic evaluations. New categories and issue detection
have not yet been accuracy-benchmarked.

## Map MVP

The two-state interactive prototype lives in `web/`. Run locally with:

```sh
.venv/bin/python -m http.server 4173 --bind 127.0.0.1 --directory web/dist
```

Open http://127.0.0.1:4173. It includes state/topic/issue filters, an enactment
timeline, search, and bill details with official sources. The 17-bill 2025
sample has proposed labels and is not a complete inventory or accuracy benchmark.
See `web/README.md` for the data contract, tests and extension path.
