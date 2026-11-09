import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from statarb import data  # noqa: E402


def fake_raw(tickers):
    idx = pd.bdate_range("2022-01-01", periods=200)
    rng = np.random.default_rng(0)
    close = pd.DataFrame({t: 100 + rng.normal(size=200).cumsum() for t in tickers}, index=idx)
    return pd.concat({"Close": close}, axis=1)


@pytest.fixture(autouse=True)
def clear_cache():
    data._cache.clear()


def test_second_call_uses_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(data, "_download", lambda t, s, e: calls.append(1) or fake_raw(t))
    a, _ = data.fetch_prices(["aaa", "bbb"], "2022-01-01", "2022-12-31")
    b, _ = data.fetch_prices(["BBB", "AAA"], "2022-01-01", "2022-12-31")  # order/case-insensitive
    assert len(calls) == 1
    b.iloc[0, 0] = -1  # mutating a result must not corrupt the cache
    c, _ = data.fetch_prices(["AAA", "BBB"], "2022-01-01", "2022-12-31")
    assert c.iloc[0, 0] != -1


def test_expiry_and_errors_not_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(data, "_download", lambda t, s, e: calls.append(1) or pd.DataFrame())
    for _ in range(2):
        with pytest.raises(ValueError):
            data.fetch_prices(["AAA", "BBB"], "2022-01-01", "2022-12-31")
    assert len(calls) == 2  # failures are retried, not cached

    monkeypatch.setattr(data, "_download", lambda t, s, e: calls.append(1) or fake_raw(t))
    data.fetch_prices(["AAA", "BBB"], "2022-01-01", "2022-12-31")
    monkeypatch.setattr(data, "CACHE_TTL", 0)
    data.fetch_prices(["AAA", "BBB"], "2022-01-01", "2022-12-31")
    assert len(calls) == 4


def fake_raw_range(starts, end="2022-12-31"):
    """Tickers that start on different dates (NaN before their start)."""
    idx = pd.bdate_range(min(starts.values()), end)
    rng = np.random.default_rng(1)
    cols = {}
    for t, st in starts.items():
        v = 100 + rng.normal(size=len(idx)).cumsum()
        v[idx < pd.Timestamp(st)] = np.nan
        cols[t] = v
    return pd.concat({"Close": pd.DataFrame(cols, index=idx)}, axis=1)


def test_short_history_suggests_available_range(monkeypatch):
    raw = fake_raw_range({"AAA": "2006-01-02", "BBB": "2008-03-03"})
    monkeypatch.setattr(data, "_download", lambda t, s, e: raw)
    df, warnings = data.fetch_prices(["AAA", "BBB"], "2006-01-01", "2022-12-31")
    msg = " ".join(warnings)
    assert "BBB starts on 2008-03-03" in msg
    assert "Maximum range available: 2008-03-03 to 2022-12-30" in msg


def test_full_range_has_no_warning(monkeypatch):
    raw = fake_raw_range({"AAA": "2020-01-01", "BBB": "2020-01-01"})
    monkeypatch.setattr(data, "_download", lambda t, s, e: raw)
    _, warnings = data.fetch_prices(["AAA", "BBB"], "2020-01-01", "2022-12-31")
    assert warnings == []


def test_row_cap_enforced_at_load_with_suggestion(monkeypatch):
    monkeypatch.setattr(data, "MAX_ROWS", 300)
    monkeypatch.setattr(data, "_download", lambda t, s, e: fake_raw_range({"AAA": "2020-01-01", "BBB": "2020-01-01"}))
    with pytest.raises(ValueError, match=r"Too many rows.*Try a start date of"):
        data.fetch_prices(["AAA", "BBB"], "2020-01-01", "2022-12-31")
