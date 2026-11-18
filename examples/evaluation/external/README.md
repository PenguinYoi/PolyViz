# External-label reviewer evaluation

`pa_primary_report.json` records a temporal holdout evaluation against the published Pennsylvania Policy Database Project primary-topic labels. It reports the filtered source population, duplicate/conflict exclusions, training/calibration/test counts, class support, primary-topic accuracy, top-three recall, and selective-score coverage. This is a different task and reference from the old 52-bill multi-label evaluation; their percentages cannot be directly compared.

`six_state_review_summary.json` records the automated review of the existing 52-bill sample. None has an exact source-label match. Its statuses are automated second opinions, not human-confirmed correctness judgments. All custom policy topics remain unverified.

See `docs/AUTOMATED_REVIEW.md` for source assessment, reproduction, limitations, and usage. No paid API or credits were used.
