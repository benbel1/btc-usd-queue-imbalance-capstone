# Coinbase BTC-USD queue imbalance capstone

Group 17831. Initial research implementation, 25 September 2026.

Question: does best-quote queue imbalance improve 10-second log mid-price return forecasts beyond recent returns, volatility, spread and depth?

## Start the pilot now

Use Python 3.12 on a computer with unrestricted access to Coinbase Exchange's public WebSocket. No Coinbase account, API key or trading permission is used. The program never places trades.

On Windows, unzip this package, install Python 3.12 if needed, and double-click `start_pilot.cmd`. Keep the computer powered, awake and connected for 48 hours. Synchronize the system clock first. The script creates a virtual environment, installs dependencies, runs tests, collects and analyzes the pilot. Do not run it from inside the ZIP. Existing output directories are deliberately not overwritten. Rename an old pilot directory before restarting.

On macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python collect.py --hours 48 --out data/pilot
python analyze.py --input data/pilot/observations.csv --out results/pilot --mode pilot
```

Optional one-minute connectivity check before the full run:

```bash
python collect.py --hours 0.016667 --out data/smoke
```

Confirm metadata contains messages and valid_seconds greater than zero. A failed check is not market evidence. Three connection errors without any valid observations stop collection. After an interruption, use a NEW output directory. Current code does not resume an old collection.

## Send back after collection

Share `data/pilot/metadata.json`, `data/pilot/observations.csv` and the `results/pilot` folder. Preserve `raw.jsonl.gz` locally for audit. Raw logs can become large, so check free disk space during the first hour. Do not upload raw data to GitHub until redistribution terms and repository size have been checked.

## Files and evidence

- `book.py`: snapshot and replacement-size level 2 updates, zero-size deletion, valid best quotes.
- `collect.py`: raw received messages and one-second book observations. Time is local receipt UTC, not exchange event time. No reconstruction of past history.
- `features.py`: causal predictors, future labels, gap/session exclusion, chronological partitions and overlap purging.
- `analyze.py`: coverage, descriptive output, ridge comparisons, daily losses and main-study bootstrap.
- `tests/test_research.py`: ten tests using synthetic fixtures solely to check software behavior.
- `results/test_run.txt`: passing test transcript from the development environment.
- `results/connectivity_check`: actual failed live connection attempt. Its original status `completed` means the process ended, not that data were collected. It contains zero messages and zero valid seconds. The revised collector explicitly returns `failed_no_market_data` with exit code 1 in this case.
- `docs/review_notes.md`: requirements, source links and method clarifications.

Dependencies are pinned to versions tested with Python 3.12.14 on Linux. Windows launch instructions have not yet been live-tested. Successful unit tests do not establish feed reliability or predictive performance.

## Evaluation

The pilot is exploratory. Models use identical eligible observations and a chronological 60/20/20 split. Alpha is selected independently for each model from 0.01, 0.1, 1, 10, 100 by validation MSE. Exact ties choose larger alpha. Scaling is fit only within the training pipeline, then refit with train plus validation. Ridge uses scikit-learn's sum-of-squares objective plus alpha times squared coefficient norm. Alpha therefore depends on sample size.

The main study requires a preselected 30-calendar-day UTC window, ideally starting at midnight. Prepare that exact window before running `--mode main`. At least 24/30 days, including 5/6 test days, must have at least 95% valid seconds. Do not choose the window after viewing forecast results. Main code rejects inputs outside the window or below coverage. The collector can record 720 hours but a start away from UTC midnight needs additional collection to supply 30 full calendar days.

Main inference resamples paired daily losses 2,000 times with seed 690. Few test days and possible cross-day dependence limit confidence. The pilot does not receive this confidence interval. Nonoverlapping ten-second observations and spread/volatility groups are sensitivity checks. These are prediction results, not simulated trading profits.

## GitHub publication

Private repository: https://github.com/benbel1/btc-usd-queue-imbalance-capstone

Source, documentation, requirements and small results belong here. `.gitignore` excludes data and environments. Professor access remains pending.

## Three-day sequence

25 September: start the pilot and publish the repository.
26 September: inspect coverage and disk usage while collection continues, review the literature and method wording.
27 September: complete the pilot, run analysis and integrate the actual temporary results.
28 September: check citations, repository access and the course's exact submission time, then submit.

The 30-day main experiment necessarily follows this literature-review deadline.
