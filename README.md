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
