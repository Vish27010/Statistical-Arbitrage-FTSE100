import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
from fastapi import FastAPI, File, HTTPException, Request, UploadFile  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from statarb.analysis import correlation_matrix, engle_granger, top_pairs  # noqa: E402
from statarb.data import fetch_prices, parse_csv  # noqa: E402

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
STATIC = Path(__file__).parent / "static"

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI(title="Stat-Arb Explorer")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class Prices(BaseModel):
    """Wide table: dates plus one price list per ticker (null = missing)."""
    dates: list[str]
    columns: dict[str, list[float | None]] = Field(max_length=20)

    def to_df(self) -> pd.DataFrame:
        df = pd.DataFrame(self.columns, index=pd.to_datetime(self.dates))
        if len(df) > 2600:
            raise HTTPException(413, "Too many rows (max ~10 years daily)")
        return df


class TickerRequest(BaseModel):
    tickers: list[str]
    start: str
    end: str


class CointRequest(BaseModel):
    prices: Prices
    ticker_y: str
    ticker_x: str
    window: int = Field(60, ge=5, le=250)
    rolling: bool = False


def _to_payload(df: pd.DataFrame, warnings: list[str]) -> dict:
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
        "columns": {c: [None if pd.isna(v) else float(v) for v in df[c]] for c in df.columns},
        "warnings": warnings,
    }


@app.post("/api/prices/tickers")
@limiter.limit("10/minute")
def prices_from_tickers(request: Request, req: TickerRequest):
    try:
        return _to_payload(*fetch_prices(req.tickers, req.start, req.end))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/prices/csv")
@limiter.limit("20/minute")
async def prices_from_csv(request: Request, file: UploadFile = File(...)):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 5MB)")
    try:
        return _to_payload(*parse_csv(content))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/correlation")
def correlation(prices: Prices):
    corr = correlation_matrix(prices.to_df())
    return {
        "tickers": list(corr.columns),
        "matrix": [[None if pd.isna(v) else float(v) for v in row] for row in corr.values],
        "top_pairs": top_pairs(corr),
    }


@app.post("/api/cointegration")
def cointegration(req: CointRequest):
    try:
        return engle_granger(req.prices.to_df(), req.ticker_y, req.ticker_x,
                             window=req.window, rolling=req.rolling)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
