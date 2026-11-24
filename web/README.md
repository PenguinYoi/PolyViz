# PolyViz map MVP

A buildless, browser-only map of 2025 bills for the 50 states and the District
of Columbia. Seventeen bills are source-checked enactments. The rest come from
`dist/data/inventory.json`: legislature-passed bills whose signatures are not
verified. All assets and data are local; there are no API keys, runtime dependencies,
remote fonts, paid inference calls or database services.

From the PolyViz repository root:

```sh
.venv/bin/python -m http.server 4173 --bind 127.0.0.1 --directory web/dist
```

Open http://127.0.0.1:4173. Plain `python3` also works; serving over HTTP is required
because the app fetches JSON. No npm install or build is needed.

GitHub Pages publishes this same `dist` folder. After the Pages workflow is on
`main`, set the repository’s Pages source to **GitHub Actions**. The project site
is served at `https://penguinyoi.github.io/PolyViz/`. Paths in the page are relative,
so they keep working under that project path. Script files use `.js` because
GitHub Pages does not reliably serve `.mjs` as JavaScript. For frontend tests:

```sh
node --test web/tests/model.test.mjs
```

## Included

- Clickable, keyboard-accessible California and Texas state shapes on a US map.
- All 16 topic filters, a specific-issue menu, related-word issue search, state selection, title/bill-number search, and a flat or raised map. Bars under the map show the largest state, topic, and issue counts in the current view and can be selected. Month bars move the timeline.
- Cumulative monthly enactment slider and play/pause.
- Sourced bill details, topic rationale and clear proposed-label status.
- Reviewed-only empty state; no machine or assistant label is silently verified.
- Responsive layout, native keyboard-dismissable dialogs, linkable URL filters.
- Methodology dialog and downloadable sample JSON.

## Data contract and limitations

`dist/data/bills.json` is an intentionally curated interface fixture, not a complete
session export or a classifier accuracy benchmark. Nine California and eight Texas records were selected for varied topics. Official-source links substantiate historical enactment;
short summaries are assistant paraphrases. Topic, issue and sector labels are
assistant proposals, not newly run classifier predictions or reviewed truth. The
classifier and its frozen evaluation files are unchanged by this UI work.

Map/list logic uses `status == enacted` and a non-null `dates.enacted` not later
than the selected month-end. Gray means no coverage, while covered states with
zero matches have a separate fill. Comparisons retain both states' filter counts
when a single state's list is selected. Topics can overlap; bills are deduplicated
by their unique ID in the source fixture. Empty reviewed-only results are expected.
Enactment dates are historical; later amendments, litigation and current legal
force are outside this snapshot. Effective dates are populated only when checked in official sources. Staged
provisions retain separate dated events; a single date is not inferred from enactment. Session identities differ:
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
The app currently supports CA and TX; add another state in `dist/model.js` and
its label position in `dist/app.js`, then update coverage text and tests together.
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


## Source checks before expansion

Run `.venv/bin/python -m polyviz.map_data web/dist/data/bills.json` from the repo
root before publication. This checks identities, coverage, controlled labels,
consistent dates, official state domains, signature-event metadata, claim-to-source
links, scope notes and provenance for reviewed labels. It is an offline metadata
gate, not a factual or semantic accuracy score. The checker currently admits the
pilot's signed-by-governor events; other lawful enactment paths need explicit
support before ingestion.

Each record includes `source_claims` with the displayed summary, an official URL,
a section/page locator, a check date and the checking method. Checks were performed
by an AI assistant, not an independent legal expert. `summary_limitations` records
important conditions. Bill details expose these notes and distinguish factual
source checking from topic-label review. No label is marked independently reviewed.

For example, CA SB 57 uses the final assessment authorization, not the earlier
special-tariff proposal. TX HB 1481 retains the disability/medical/safety exceptions.
TX SB 38 retains its staged effective dates. Projected benefits in government press
releases are not presented as measured outcomes. This remains a selective sample,
not a full statutory digest or a current-enforceability database.
