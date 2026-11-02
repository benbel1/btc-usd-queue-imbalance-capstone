# Coinbase BTC-USD queue imbalance capstone

Group 17831. Formal study completed 2 November 2026.

## Formal study results

[Read the formal study results and analysis code](formal-study/). On 505,117 held-out forecasts, queue imbalance reduced ridge MSE by 0.752% but increased MAE by 1.126%. The approximate paired-day 95% interval for MSE improvement was 0.480%–1.300%, based on six UTC days.

Question: does best-quote queue imbalance improve 10-second log mid-price return forecasts beyond recent returns, volatility, spread and depth?

## Completed pilot

The 48-hour pilot ran from 25 September 2026 20:45:37 UTC to 27 September 20:45:37 UTC. It recorded 2,861,006 messages, 172,800 observation seconds and 172,022 valid seconds (99.55%). Of 171,455 eligible rows, 20 were purged; training, validation and test contained 102,670, 34,550 and 34,215 rows.

Adding imbalance reduced test MSE from 1.860426 to 1.841005 bps² (1.0439%) but increased MAE from 0.782774 to 0.810912 bps (3.5947%). The zero-return MSE was 1.858609 bps² and MAE 0.777047 bps. One test calendar day is insufficient for the planned daily-block inference. Results are exploratory, not evidence of trading profitability.

See [pilot metrics](results/pilot_summary.json), [coverage](results/pilot_coverage.csv), [descriptive statistics](results/pilot_descriptive_statistics.csv), [distribution figure](results/pilot_distributions.png), and [interruptions](results/PILOT_INTERRUPTION_SUMMARY.md).

The [research handoff ZIP](results/BTC-pilot-research-handoff-20260927T222759Z.zip) contains the pilot evidence and original scripts with machine-specific path strings redacted for publication. The repository root contains the revised portable scripts. Start with its README_RESEARCH_HANDOFF.md. MANIFEST.json records regenerated SHA-256 hashes for the publication copy. The original verified handoff remains preserved privately. Raw feed logs, credentials and environments are excluded. Retain raw logs on the collection host. Historical verification statements refer to their stated times, not the final run status.

## Running a new collection

The completed pilot does not need restarting. Running the launcher starts a NEW collection. Use Python 3.12 and a host with access to Coinbase Exchange's public WebSocket. No Coinbase account, API key or trading permission is used; the program never places trades.

### Portable launcher

Keep `monitor_pilot.py` and `start_pilot.cmd` in the repository root. Install Python 3.12, create and activate a virtual environment, then install `requirements.txt`. On Windows:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
start_pilot.cmd --hours 48
```

The Windows launcher uses `CAPSTONE_PYTHON` if set, then the checkout's `.venv`, otherwise `python` on PATH. It contains no personal paths. The monitor defaults to the directory containing itself, regardless of the terminal's working directory. Use `--project-dir` for a separate checkout and `--data-dir` for a writable output location; quote paths containing spaces. Existing outputs are never reused.

On macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python monitor_pilot.py --hours 48
```

Use `--hours 0.025` for a 90-second verification. The revised portable supervisor retains the pilot monitoring and analysis logic; the completed pilot used its earlier Windows-specific layout. Python unit tests and local path checks cover the revision; its Windows batch entry point still needs a Windows smoke test. Keep the host powered, awake and online. The supervisor records alerts locally; it is not reboot-persistent and does not send push notifications.

Optional one-minute connectivity check before the full run:

```bash
python collect.py --hours 0.016667 --out data/smoke
```

Confirm metadata contains messages and valid_seconds greater than zero. A failed check is not market evidence. Three connection errors without any valid observations stop collection. After an interruption, use a NEW output directory. Current code does not resume an old collection.

## Collection outputs

Each supervised run writes collection metadata and observations under its `collection` directory and analysis outputs under `results`. Preserve `raw.jsonl.gz` locally for audit. Raw logs can become large, so check free disk space during the first hour. Do not upload raw data to GitHub until redistribution terms and repository size have been checked.

## Files and evidence

- `book.py`: snapshot and replacement-size level 2 updates, zero-size deletion, valid best quotes.
- `collect.py`: raw received messages and one-second book observations. Time is local receipt UTC, not exchange event time. No reconstruction of past history.
- `features.py`: causal predictors, future labels, gap/session exclusion, chronological partitions and overlap purging.
- `analyze.py`: coverage, descriptive output, ridge comparisons, daily losses and main-study bootstrap.
- `tests/test_research.py`: ten tests using synthetic fixtures solely to check software behavior.
- `results/test_run.txt`: passing test transcript from the development environment.
- `results/connectivity_check`: actual failed live connection attempt. Its original status `completed` means the process ended, not that data were collected. It contains zero messages and zero valid seconds. The revised collector explicitly returns `failed_no_market_data` with exit code 1 in this case.
- `docs/review_notes.md`: source audit and method definitions.

Dependencies are pinned. The completed Windows pilot used Python 3.12.5, NumPy 2.3.5, pandas 2.2.3 and scikit-learn 1.8.0. The earlier failed cloud connectivity attempt is retained as historical evidence; the completed Windows pilot supersedes it for live collection status.

## Evaluation

The pilot is exploratory. Models use identical eligible observations and a chronological 60/20/20 split. Alpha is selected independently for each model from 0.01, 0.1, 1, 10, 100 by validation MSE. Exact ties choose larger alpha. Scaling is fit only within the training pipeline, then refit with train plus validation. Ridge uses scikit-learn's sum-of-squares objective plus alpha times squared coefficient norm. Alpha therefore depends on sample size.

The main study requires a preselected 30-calendar-day UTC window, ideally starting at midnight. Prepare that exact window before running `--mode main`. At least 24/30 days, including 5/6 test days, must have at least 95% valid seconds. Do not choose the window after viewing forecast results. Main code rejects inputs outside the window or below coverage. The collector can record 720 hours but a start away from UTC midnight needs additional collection to supply 30 full calendar days.

Main inference resamples paired daily losses 2,000 times with seed 690. Few test days and possible cross-day dependence limit confidence. The pilot does not receive this confidence interval. Nonoverlapping ten-second observations and spread/volatility groups are sensitivity checks. These are prediction results, not simulated trading profits.

## GitHub publication

Repository: https://github.com/benbel1/btc-usd-queue-imbalance-capstone

The repository contains source code, documentation, pinned requirements and pilot results. `.gitignore` excludes new collection data and Python environments.

## Next phase

The main study will use a prospectively selected thirty-day UTC window with frozen model specifications. A durable cloud collector must be deployed and verified before that collection begins.
