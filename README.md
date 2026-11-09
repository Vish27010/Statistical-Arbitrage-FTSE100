# Iterative Development of a Statistical Arbitrage Framework

## Project Vision
This project developed an automated trading framework to exploit mean-reversion opportunities within the FTSE 100. It operates on the theoretical premise that economically linked pairs maintain a long-term equilibrium, where deviations represent tradable alpha.

## Phase 1: Universe Selection & Stock Selection
Rather than "data mining" random combinations, stocks were selected based on a top-down **Fundamental Driver Hypothesis**:

* **Financials (Interest Rate Sensitivity):** `HSBA.L` vs. `BARC.L`.
* **Energy (Commodity Exposure):** `SHEL.L` vs. `BP.L`.
* **Mining (Global Industrial Demand):** `RIO.L` vs. `GLEN.L`.

**Criteria for Selection:**
1.  **High Cointegration:** Identifying pairs where the "spread" distance historically reverts to a constant mean.
2.  **Sector Alignment:** Ensuring both tickers react to the same systemic shocks (e.g., Oil price fluctuations for Energy pairs).
3.  **Liquidity:** Focusing on FTSE 100 constituents to minimize slippage and ensure trade execution.

## Phase 2: The Iterative Engineering Process
The framework was built through several stages of refinement to bridge the gap between theory and execution:

* **Hedge Engine:** Implemented a Rolling OLS regression to calculate a dynamic hedge ratio ($\beta$).
* **Signal Tuning:** Iterated through various Z-score sensitivities (initially 1.5, stabilized at 2.0) and lookback windows (60 days) to optimize entry timing.
* **Operational Constraints:** Accounted for a 5bps (0.05%) transaction fee and a "warm-up" period for rolling calculations.

## Phase 3: The "Beta Drift" Discovery (The Pivot)
During development, a version of the model reported a **1.97 Sharpe Ratio**. Forensic analysis revealed this was an artifact of calculating returns using `spread.diff()`.

* **The Problem:** `spread.diff()` incorrectly credits the daily change in the Beta coefficient as profit.
* **The Solution:** Re-engineered the backtest to use an **"Honest Cash PnL"** calculation. This locks the hedge ratio at the time of entry, reflecting actual share ownership.
* **The Result:** The Sharpe Ratio adjusted to **0.02**, providing a realistic baseline of the strategy’s net-of-fee performance.



## Phase 4: Lessons Learned
* **Backtest Artifacts:** High performance in early iterations was driven by "Beta Drift," a common pitfall in rolling regression models.
* **Execution Friction:** Even small fees (5bps) significantly impact high-frequency mean reversion strategies.
* **Regime Shifts:** Late 2025 data showed a "Pair Breakup," highlighting the need for hard stop-losses when statistical relationships decouple.

## Future Work
The framework is modular and ready for the implementation of **Kalman Filters** for smoother hedge ratios or **Time-Exit** logic to mitigate the impact of prolonged divergence.

## Web app

**Live demo: https://statistical-arbitrage-ftse100.onrender.com/**

A FastAPI + Plotly tool: load prices (Yahoo tickers or a wide CSV), view the correlation matrix of daily returns, run an Engle-Granger cointegration test on any pair, and plot the spread and z-score. The free hosting tier sleeps when idle, so the first load after a quiet spell can take a while.

**Using it**
1. Enter tickers in Yahoo format (e.g. `HSBA.L, BARC.L`) with a date range, or upload a wide CSV (first column dates, one column per ticker).
2. Click a cell in the correlation heatmap to select that pair.
3. Read the Engle-Granger p-value, hedge ratio, half-life and the spread and z-score charts. Optionally use a rolling hedge ratio.

**Limits:** up to 20 tickers, 5000 daily rows (about 20 years) and 5MB per CSV. If your range is longer than the available data, the app tells you the maximum range it can use. Yahoo fetches are cached for 15 minutes.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload     # http://localhost:8000
.venv/bin/python -m pytest tests            # tests
docker build -t statarb . && docker run -p 8000:8000 statarb
```

Layout: `src/statarb/` holds the analysis library (no web code), `app/` the API and static frontend. Cointegration is tested in-sample and is not a trading signal.
