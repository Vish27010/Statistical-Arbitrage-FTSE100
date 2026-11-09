"""Pure analysis functions: correlation, cointegration, hedge ratio, spread."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS
from statsmodels.tsa.stattools import adfuller, coint

MIN_OBS = 100


def correlation_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Correlation of daily returns (price levels give spurious correlation)."""
    return prices.pct_change().dropna(how="all").corr()


def top_pairs(corr: pd.DataFrame, n: int = 10) -> list[dict]:
    cols = list(corr.columns)
    out = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            v = corr.loc[a, b]
            if pd.notna(v):
                out.append({"a": a, "b": b, "corr": float(v)})
    return sorted(out, key=lambda d: d["corr"], reverse=True)[:n]


def hedge_ratio(y: pd.Series, x: pd.Series) -> tuple[float, float]:
    """OLS y = alpha + beta * x. Returns (alpha, beta)."""
    X = sm.add_constant(x.rename("x"))
    params = sm.OLS(y, X).fit().params
    return float(params["const"]), float(params["x"])


def rolling_hedge_ratio(y: pd.Series, x: pd.Series, window: int = 60) -> pd.DataFrame:
    """Rolling OLS alpha/beta. Shifted one step so row t only uses data before t."""
    X = sm.add_constant(x.rename("x"))
    p = RollingOLS(y, X, window=window).fit().params
    return p.shift(1).rename(columns={"const": "alpha", "x": "beta"})


def spread(y, x, alpha, beta):
    return y - beta * x - alpha


def zscore(s: pd.Series, window: int = 60) -> pd.Series:
    return (s - s.rolling(window).mean()) / s.rolling(window).std()


def half_life(s: pd.Series) -> float | None:
    """Mean-reversion half-life (days) from AR(1) on the spread."""
    lag = s.shift(1).dropna()
    delta = s.diff().dropna()
    lag, delta = lag.align(delta, join="inner")
    b = sm.OLS(delta, sm.add_constant(lag)).fit().params.iloc[1]
    if b >= 0:
        return None  # not mean reverting
    return float(-np.log(2) / b)


def engle_granger(prices: pd.DataFrame, ticker_y: str, ticker_x: str,
                  window: int = 60, rolling: bool = False) -> dict:
    for t in (ticker_y, ticker_x):
        if t not in prices.columns:
            raise ValueError(f"Unknown ticker: {t}")
    if ticker_y == ticker_x:
        raise ValueError("Choose two different tickers")
    df = prices[[ticker_y, ticker_x]].dropna()
    if len(df) < MIN_OBS:
        raise ValueError(f"Need at least {MIN_OBS} overlapping rows, got {len(df)}")
    y, x = df[ticker_y], df[ticker_x]

    t_stat, p_value, crit = coint(y, x)
    alpha, beta = hedge_ratio(y, x)

    if rolling:
        rh = rolling_hedge_ratio(y, x, window)
        s = (y - rh["beta"] * x - rh["alpha"]).dropna()
    else:
        s = spread(y, x, alpha, beta)
    adf_p = float(adfuller(s.dropna(), result_object=False)[1])
    z = zscore(s, window)

    def series(v: pd.Series) -> list:
        return [None if pd.isna(i) else float(i) for i in v]

    return {
        "ticker_y": ticker_y, "ticker_x": ticker_x, "n_obs": int(len(df)),
        "t_stat": float(t_stat), "p_value": float(p_value),
        "critical_values": {"1%": float(crit[0]), "5%": float(crit[1]), "10%": float(crit[2])},
        "alpha": alpha, "beta": beta,
        "adf_p_value": adf_p, "half_life": half_life(s.dropna()),
        "cointegrated_5pct": bool(p_value < 0.05),
        "dates": [d.strftime("%Y-%m-%d") for d in s.index],
        "spread": series(s), "zscore": series(z.reindex(s.index)),
    }
