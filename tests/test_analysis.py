import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from statarb.analysis import correlation_matrix, engle_granger  # noqa: E402


def make_prices(cointegrated: bool, n=500, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = 100 + np.cumsum(rng.normal(size=n))
    if cointegrated:
        noise = np.zeros(n)
        for i in range(1, n):  # stationary AR(1) spread
            noise[i] = 0.7 * noise[i - 1] + rng.normal()
        y = 5 + 1.5 * x + noise
    else:
        y = 100 + np.cumsum(rng.normal(size=n))
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({"A": y, "B": x}, index=idx)


def test_cointegrated_pair():
    r = engle_granger(make_prices(True), "A", "B")
    assert r["p_value"] < 0.05
    assert abs(r["beta"] - 1.5) < 0.1
    assert r["half_life"] is not None


def test_random_walks_not_cointegrated():
    assert engle_granger(make_prices(False, seed=3), "A", "B")["p_value"] > 0.05


def test_rolling_runs():
    r = engle_granger(make_prices(True), "A", "B", rolling=True)
    assert len(r["spread"]) == len(r["zscore"])


def test_bad_inputs():
    p = make_prices(True)
    for args in (("A", "Z"), ("A", "A")):
        try:
            engle_granger(p, *args)
            assert False
        except ValueError:
            pass


def test_correlation_symmetric():
    c = correlation_matrix(make_prices(True))
    assert c.loc["A", "B"] == c.loc["B", "A"]
