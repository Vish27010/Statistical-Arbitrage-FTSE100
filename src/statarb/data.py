"""Load price data from yfinance or an uploaded CSV into a wide DataFrame."""
from __future__ import annotations

import io

import pandas as pd

MAX_TICKERS = 20
MIN_OBS = 100


def _clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    df = df.apply(pd.to_numeric, errors="coerce").sort_index()
    df = df.dropna(axis=1, how="all")
    if df.shape[1] < 2:
        raise ValueError("Need at least 2 columns of price data")
    if df.shape[1] > MAX_TICKERS:
        raise ValueError(f"At most {MAX_TICKERS} tickers allowed")
    sparse = [c for c in df.columns if df[c].notna().sum() < MIN_OBS]
    if sparse:
        warnings.append(f"Dropped (fewer than {MIN_OBS} rows): {', '.join(sparse)}")
        df = df.drop(columns=sparse)
    df = df.ffill(limit=3)
    if df.shape[1] < 2 or len(df.dropna()) < MIN_OBS:
        raise ValueError(f"Fewer than {MIN_OBS} overlapping rows across tickers")
    return df, warnings


def parse_csv(content: bytes) -> tuple[pd.DataFrame, list[str]]:
    """Wide CSV: first column is the date, remaining columns are prices."""
    try:
        df = pd.read_csv(io.BytesIO(content), index_col=0, parse_dates=True)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Could not read CSV: {e}") from e
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("First CSV column must contain dates")
    return _clean(df)


def fetch_prices(tickers: list[str], start: str, end: str) -> tuple[pd.DataFrame, list[str]]:
    import yfinance as yf

    tickers = list(dict.fromkeys(t.strip().upper() for t in tickers if t.strip()))
    if len(tickers) < 2:
        raise ValueError("Enter at least 2 tickers")
    if len(tickers) > MAX_TICKERS:
        raise ValueError(f"At most {MAX_TICKERS} tickers allowed")
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError("No data returned; check tickers and dates")
    close = raw["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    missing = [t for t in tickers if t not in close.columns or close[t].isna().all()]
    df, warnings = _clean(close)
    if missing:
        warnings.insert(0, f"No data for: {', '.join(missing)}")
    return df, warnings
