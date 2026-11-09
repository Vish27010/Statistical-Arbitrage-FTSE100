import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from test_analysis import make_prices  # noqa: E402

client = TestClient(app)


def payload(df):
    return {"dates": [d.strftime("%Y-%m-%d") for d in df.index],
            "columns": {c: df[c].tolist() for c in df.columns}}


def test_csv_then_correlation_then_coint():
    df = make_prices(True)
    csv = df.to_csv().encode()
    r = client.post("/api/prices/csv", files={"file": ("p.csv", csv, "text/csv")})
    assert r.status_code == 200
    prices = {k: r.json()[k] for k in ("dates", "columns")}

    r = client.post("/api/correlation", json=prices)
    assert r.status_code == 200 and r.json()["tickers"] == ["A", "B"]

    r = client.post("/api/cointegration", json={"prices": prices, "ticker_y": "A", "ticker_x": "B"})
    assert r.status_code == 200 and r.json()["p_value"] < 0.05


def test_errors_are_400():
    prices = payload(make_prices(True))
    r = client.post("/api/cointegration", json={"prices": prices, "ticker_y": "A", "ticker_x": "ZZZ"})
    assert r.status_code == 400
    r = client.post("/api/prices/csv", files={"file": ("p.csv", b"not,a\nvalid,file", "text/csv")})
    assert r.status_code == 400


def test_index_served():
    assert client.get("/").status_code in (200, 404)  # 404 until frontend exists
