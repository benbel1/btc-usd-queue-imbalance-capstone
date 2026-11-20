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

## Return-size decomposition

The final report's Tables 4a and 4b are reproduced by [return_size.py](return_size.py) and available as [return_size.csv](results/return_size.csv). This is a retrospective, explanatory analysis of the same 505,117 held-out predictions. No models are fitted or tuned.

Exact-zero realised ten-second returns are separate. The remaining absolute-return bands are (0,1], (1,2], (2,5] and >5 basis points; finite upper endpoints are included. Augmented ridge has lower mean absolute error in all four nonzero bands, but the penalty on unchanged endpoints outweighs those gains. The 2–5 bp band contributes the largest share of the net MSE improvement.

### Run locally

From the repository root, create a Python 3.12 virtual environment using the root README instructions, then run:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python formal-study/return_size.py "/path/to/held_out_predictions.csv" "/path/to/new-return-size.csv"
```

Use normal Python, without the `-O` flag: the archived script uses assertions to check inputs and loss reconciliation. Choose a new output filename; this script overwrites the supplied output path.

Input: `results/held_out_predictions.csv` from the preserved formal-results archive, with columns `timestamp,target,baseline,augmented,zero`. Targets and predictions are in basis points. Use the complete file, not a sample. It is not included in this repository; obtain the study archive from the project authors for reproduction. The code's fixed row-count check intentionally applies to this study only.

The published script is byte-identical to the script used for the report. On 20 November 2026 it was rerun on the saved predictions; its CSV matched the previously generated file byte for byte. [Verification hashes](results/return_size_verification.json) identify the input, script and output.

The contribution columns are weighted baseline-minus-augmented losses (or zero-minus-augmented for `vs_zero`). Sum contributions across bands to recover the corresponding whole-sample loss difference. They are not percentages. Band membership uses future realised returns and cannot select a forecast at decision time.

The frozen formal fitting scripts remain unchanged. Their Windows memory checks and preserved-input requirements still apply; the new decomposition script itself uses portable file-path arguments.
