# Coinbase BTC–USD formal study

**Study period:** 2–31 October 2026 UTC. Valid coverage was 99.805%. Of 2,524,833 eligible rows after purging, 505,117 belonged to the six held-out days. Both ridge models used the same rows and predicted ten-second log midpoint returns.

| Forecast | Validation-selected penalty | MSE (bp²) | RMSE (bp) | MAE (bp) |
|---|---:|---:|---:|---:|
| Baseline ridge | 0.01 | 4.847030 | 2.201597 | 1.319306 |
| Ridge with queue imbalance | 100 | 4.810569 | 2.193301 | 1.334162 |
| Zero return | — | 4.847136 | 2.201621 | 1.315213 |

Adding imbalance lowered MSE by 0.752% but increased MAE. The approximate paired-day bootstrap interval was 0.480%–1.300%; only six days support it. The frozen low-spread group had no test rows. The leave-one-day-out analysis is exploratory and used the existing predictions without refitting.

## Inspect the evidence

- [All metrics and penalties](results/summary.json) · [Daily paired losses](results/daily_paired_losses.csv) · [Coverage and eligible rows](results/daily_coverage_eligibility.csv)
- [Sensitivity checks](results/sensitivity_results.json) · [Leave-one-day-out results](results/exploratory_leave_one_test_day_out.csv) · [Prediction verification](results/post_analysis_verification.json)
- [Reviewed segment assembler](source/ops/assemble_reviewed.py) · [Feature and target definitions](source/features.py) · [Ridge comparison and bootstrap](source/analyze.py)
- [Feature preparation](run_frozen_analysis.py) · [Formal fit from checkpoint](resume_frozen_analysis.py) · [Runtime configuration and source hashes](results/execution_configuration.json)

The execution scripts record the Windows analysis workflow. Replaying the fit requires the separately preserved study inputs and checkpoint layout. The nine hash-pinned zero-valid exceptions preserve invalid rows and gaps. The original evidence archive retains full predictions, logs, figures and file hashes.
