# Source audit and method definitions

## Research scope

The comparative analysis considers published research addressing related prediction problems. Differences in venue, target horizon and input data limit direct comparisons of reported model performance.

## Method definitions

Resting bid and ask quantities measure displayed depth, not traded volume. Queue imbalance is (bid quantity - ask quantity)/(bid quantity + ask quantity). The target is 10,000 ln(mid[t+10]/mid[t]). Daily candles cannot reconstruct these measurements. The completed 48-hour pilot uses public live data. The planned main study requires a prospectively selected thirty-day UTC window and frozen model specifications. Coverage must reach 95% valid seconds on at least 24/30 days, including at least five test days. The planned positive-result criterion requires the whole approximate confidence interval to exceed zero. Independence across daily blocks is an assumption.

## Source matrix

Search checked 25 September 2026. Targeted primary-source review, not a systematic review. Preprints are identified separately. No numerical performance comparison across incompatible targets is used.

| Source | Material consulted | Contribution and limitation |
|---|---|---|
| Gould and Bonart (2015), https://arxiv.org/abs/1512.03492 | Full author preprint | Queue imbalance and next-move direction. Equity event horizon differs from fixed ten-second crypto returns. |
| Cont, Kukanov and Stoikov (2014), https://doi.org/10.1093/jjfinec/nbt003 ; https://arxiv.org/abs/1011.6402 | Full author preprint and publication metadata | Order flow imbalance and price impact. Contemporaneous explanation is not a forward forecast. |
| Zhang, Zohren and Roberts (2019), https://doi.org/10.1109/TSP.2019.2907260 ; https://arxiv.org/abs/1808.03668 | Full author manuscript | DeepLOB representation and sequence models. Different target and inputs prevent direct score comparison. |
| Schnaubelt, Rende and Krauss (2019), https://doi.org/10.3390/jrfm12010025 | Publisher-indexed abstract and passages, institutional record | Historical BTC order-book characteristics. Descriptive evidence is not a current venue measurement. |
| Albers et al. (2021), https://arxiv.org/abs/2108.09750 | Full author preprint | Cross-market Bitcoin information and fees. Single-venue design omits these signals. |
| Kolm, Turiel and Westray (2023), https://doi.org/10.1111/mafi.12413 | Publisher abstract and publication metadata | Stationary order-flow inputs and horizon. Full empirical tables not independently assessed. |
| Lucchese, Pakkanen and Veraart (2024), https://doi.org/10.1016/j.ijforecast.2024.02.001 ; https://arxiv.org/abs/2211.13777 | Full author manuscript and author publication record | Formal inference, representations and horizon sensitivity. Equity evidence needs fresh crypto test. |
| Bieganowski and Ślepaczuk (2026), https://arxiv.org/abs/2602.00776 | Full preprint v1 | Interpretable short-horizon crypto forecasting. Not treated as peer-reviewed confirmation. |
| Coinbase, https://docs.cdp.coinbase.com/exchange/websocket-feed/channels | Official current documentation | Public level2_batch and heartbeat, snapshot/update semantics. Does not prove local connectivity. |
| scikit-learn, https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html | Official documentation | Ridge objective and parameters. Installed version is pinned separately. |
