# Larger classifier evaluation

**Exploratory results against provisional assistant annotations—not independently verified accuracy.**

## Results

| Method | Exact topic sets | Label precision | Label recall | Label F1 | Extra labels | Missed labels |
|---|---:|---:|---:|---:|---:|---:|
| keyword | 28/52 (53.8%) | 81.2% | 55.3% | 65.8% | 6 | 21 |
| semantic | 21/52 (40.4%) | 55.8% | 51.1% | 53.3% | 19 | 23 |
| hybrid | 27/52 (51.9%) | 78.8% | 55.3% | 65.0% | 7 | 21 |

Exact match means the entire topic set agrees. Precision measures how many predicted topic labels agree with the reference; recall measures how many reference labels were found. F1 balances the two. These are label-level micro averages, not the percentage of bills correctly classified.

## Interpretation

- The hybrid did not outperform the keyword baseline on this larger sample. The earlier 6/6 development result did not generalize.
- Many misses are topic vocabulary or context gaps: abandoned vehicles, accessory dwellings, grand-jury procedure, forensic review, and workforce development.
- Extra education labels appeared for student election workers and school-tax exemptions: mentions are being mistaken for substantive education provisions.
- The hybrid sometimes treats civil eviction procedure as criminal justice or supportive housing as healthcare without enough supporting description.
- Some disagreements are reference-policy questions rather than clear errors. The 21 premarked ambiguous cases need human adjudication. No labels or thresholds were revised after inference.

## Clearer-reference subset

| Method | Exact topic sets (31 bills) | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| keyword | 20/31 (64.5%) | 86.4% | 67.9% | 76.0% |
| semantic | 15/31 (48.4%) | 63.0% | 60.7% | 61.8% |
| hybrid | 19/31 (61.3%) | 81.8% | 64.3% | 72.0% |

The clearer subset was identified before predictions. It is easier by design and is not a substitute for full-sample results.

## Hybrid results by topic

| Topic | Expected labels | Precision | Recall |
|---|---:|---:|---:|
| education | 2 | 25.0% | 50.0% |
| elections | 8 | 100.0% | 62.5% |
| energy | 0 | — | — |
| environment | 3 | 100.0% | 33.3% |
| healthcare | 3 | 50.0% | 33.3% |
| housing | 4 | 75.0% | 75.0% |
| labor | 4 | 66.7% | 50.0% |
| public_safety | 9 | 75.0% | 33.3% |
| taxation | 8 | 100.0% | 87.5% |
| transportation | 6 | 100.0% | 50.0% |

Energy has no expected positive examples in this sample; its performance is unmeasured. Other topic counts are also too small for strong topic-specific claims.

## Scope and limitations

- 52 new real bills across CA (10), TX (10), FL (10), NY (7), IL (5), WA (10). Previous development/evaluation bills were excluded.
- 60 URLs were selected from the first listing page for each state/session using a fixed seed; eight unavailable detail pages were excluded before classification. Sources, sampling frames, and exclusions are recorded in selection.json.
- This is a recency-biased convenience sample, not a random sample of all U.S. laws or all enacted bills. Florida is especially concentrated in local-district legislation.
- Statuses were intentionally kept unknown: this evaluates topics, not enactment recognition. Titles and summaries were obtained through public web lookup; no paid API was used.
- Labels were assigned by the assistant before predictions using only the supplied title/summary, with rationales and uncertainty flags. They are not human-reviewed ground truth.
- Classifier files, taxonomy, data, and labels were hashed before inference; hashes were verified unchanged afterward. Evaluation/reporting code was expanded, not the classifier.

## Next step

Have a human independently fill in blind_review.json, agree on category boundaries, and adjudicate disagreements. Use this sample as development data after reviewing it; reserve new bills for the next untouched test. Broaden categories for civil rights/privacy, general government, finance/business, and family law, or explicitly document them as outside scope. Include energy examples. Collect more substantive summaries where descriptions are too short. Do not publish automatic map totals as trusted classifications yet.

See README.md for reproduction commands; review_queue.json contains all hybrid/reference disagreements.
