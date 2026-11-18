# PolyViz map MVP

A buildless, browser-only map of eight sourced 2025 enactments in California and
Texas. All assets and data are local; there are no API keys, runtime dependencies,
remote fonts, paid inference calls or database services.

From the PolyViz repository root:

```sh
.venv/bin/python -m http.server 4173 --bind 127.0.0.1 --directory web/dist
```

Open http://127.0.0.1:4173. Plain `python3` also works; serving over HTTP is required
because the app fetches JSON. No npm install or build is needed. For frontend tests:

```sh
node --test web/tests/model.test.mjs
```

## Included

- Clickable, keyboard-accessible California and Texas state shapes on a US map.
- All 16 topic filters, specific issues, state selection, title/bill-number search.
- Cumulative monthly enactment slider and play/pause.
- Sourced bill details, topic rationale and clear proposed-label status.
- Reviewed-only empty state; no machine or assistant label is silently verified.
- Responsive layout, native keyboard-dismissable dialogs, linkable URL filters.
- Methodology dialog and downloadable sample JSON.

## Data contract and limitations

`dist/data/bills.json` is an intentionally curated interface fixture, not a complete
session export or a classifier accuracy benchmark. Four records per state were
selected for varied topics. Official-source links substantiate historical enactment;
short summaries are assistant paraphrases. Topic, issue and sector labels are
assistant proposals, not newly run classifier predictions or reviewed truth. The
classifier and its frozen evaluation files are unchanged by this UI work.

Map/list logic uses `status == enacted` and a non-null `dates.enacted` not later
than the selected month-end. Gray means no coverage, while covered states with
zero matches have a separate fill. Comparisons retain both states' filter counts
when a single state's list is selected. Topics can overlap; bills are deduplicated
by their unique ID in the source fixture. Empty reviewed-only results are expected.
Enactment dates are historical; later amendments, litigation and current legal
force are outside this snapshot. Effective dates are intentionally null pending
verification, rather than inferred from enactment. Session identities differ:
California's 2025–2026 regular session versus Texas's 89th regular session; this
view is a **2025 enactment-year slice**, not two equivalent completed sessions.

All 16 categories and all starter issue tags are visible even where the sample
has no matches. This avoids treating unavailable examples as unsupported filters.
The map is not population-normalized and cannot establish legislative priorities
or policy effects. State counts are recalculated for topic, issue, search, review
status and timeline filters.

## Extending the pilot

Replace or extend `dist/data/bills.json` with schema-v2 records plus the display
metadata used by the sample (`sources`, `summary_provenance`, and classification
`evidence` with an exact `excerpt`). Keep bill IDs stable; deduplicate before
export. Require verified enactment dates and retain provenance. Do not turn
`issue_classification.candidates` into assigned labels without an explicit decision.
The app currently supports CA and TX; add another state in `dist/model.mjs` and
its label position in `dist/app.mjs`, then update coverage text and tests together.
The timeline is deliberately fixed to 2025 for this MVP.

The next data step is a reproducible export from the classifier pipeline, with
machine predictions displayed separately from reviewed assignments. The initial
fixture deliberately makes that distinction visible before automated ingestion.

## Geometry and private hosting

`dist/data/states.json` contains SVG paths decoded from us-atlas v3's
`states-albers-10m.json`, an Albers USA projection derived from US Census geometry.
Source: https://github.com/topojson/us-atlas. ISC license is retained in
`dist/assets/us-atlas-LICENSE.txt`. No map service or token is needed.

`.openai/hosting.json` retains the private Sites project identity. Only this web
project is staged for publication; training data, model caches, credentials and
other PolyViz repository history are excluded. Private preview access remains
owner-only.
