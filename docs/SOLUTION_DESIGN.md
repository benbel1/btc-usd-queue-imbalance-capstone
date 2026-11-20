# Solution Design Document

Queue imbalance and ten-second returns in the Coinbase BTC–USD market

WorldQuant University | MScFE 690 | Group 17831 | November 2026

## Purpose and scope

Determine whether the balance of displayed buying and selling quantities at the best quote improves ten-second midpoint-return forecasts beyond recent returns, volatility, spread and total depth. The solution is a research pipeline for one venue and BTC–USD. It does not place orders or measure trading profitability.

## Specifications

Input: public Coinbase Exchange level2_batch and heartbeat messages, sampled once per UTC second. Study: 2 October to 1 November 2026, with the end excluded. Output: coverage records, eligible observations, three comparable forecasts, error metrics and evidence files. Python 3.12 and the pinned requirements.txt packages support execution.

## Solution architecture and code responsibilities

| Stage | Responsibility |
|---|---|
| Receive and preserve | book.py and collect.py reconstruct the best quotes, record observations and retain received messages. |
| Combine and validate | formal-study/source/ops/assemble_reviewed.py combines recording segments and retains gaps and invalid periods. |
| Build and compare | features.py defines predictors, labels and eligible rows. analyze.py fits baseline and augmented ridge models and compares them with a zero-return forecast. |
| Explain and reproduce | formal-study/return_size.py groups saved predictions by realised return size, producing band losses without refitting. README files explain installation, inputs and execution. |

## Quality controls and evaluation

A forecast requires 71 consecutive valid seconds in one recording session; missing quotes are not filled. Time-based training, validation and test partitions prevent future labels crossing boundaries. Each ridge model selects its penalty independently using validation MSE. Coverage gates, source hashes, tests and saved predictions support verification. The paired-day interval uses six test days and has limited precision.

## Delivered outcome and operating requirements

The formal sample contains 2,524,833 eligible rows after purging and 505,117 test forecasts. Adding imbalance reduced MSE by 0.752% and increased MAE by 1.126%. The return-size analysis explains the loss trade-off retrospectively; it is not a rule available at forecast time. Replaying the full historical study requires the preserved study inputs; the repository alone does not contain all raw data. A new live collection requires a continuously powered, connected host and sufficient storage.

Repository: https://github.com/benbel1/btc-usd-queue-imbalance-capstone
