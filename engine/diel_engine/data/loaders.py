"""Loader & generator data.

- load_csv: baca OHLC dari CSV (format umum HistData/broker-export).
- synthetic_bars: generator deterministik (seed) untuk demo & test tanpa jaringan.

Engine tidak peduli sumber data; ia hanya menerima objek Bars. Ini sengaja:
ingester nyata (Dukascopy) tinggal menghasilkan Bars yang sama.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .models import Bars, get_symbol


def load_csv(
    path: str,
    symbol: str,
    timeframe: str,
    *,
    timestamp_col: str = "timestamp",
    tz: str = "UTC",
) -> Bars:
    """Baca CSV ber-kolom timestamp,open,high,low,close,volume.

    Kolom volume opsional (diisi 0 kalau tidak ada). Timestamp diparse ke UTC.
    """
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    df = df.rename(columns={cols.get(k, k): k for k in
                            ["open", "high", "low", "close", "volume"] if k in cols})
    ts = pd.to_datetime(df[cols.get(timestamp_col.lower(), timestamp_col)], utc=True)
    df = df.set_index(pd.DatetimeIndex(ts))
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    return Bars(symbol=symbol.upper(), timeframe=timeframe, df=df)


_TF_MINUTES = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440,
}


def timeframe_minutes(timeframe: str) -> int:
    tf = timeframe.upper()
    if tf not in _TF_MINUTES:
        raise KeyError(f"Timeframe '{timeframe}' tidak dikenal")
    return _TF_MINUTES[tf]


def synthetic_bars(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    n: int = 2000,
    *,
    seed: int = 42,
    start: str = "2020-01-01",
    start_price: float = 1.10,
    drift: float = 0.00002,
    vol: float = 0.0010,
) -> Bars:
    """Random-walk OHLC deterministik (seeded) untuk demo/test.

    Bukan data pasar nyata — hanya untuk membuktikan engine berjalan end-to-end
    tanpa jaringan. Dengan seed tetap, hasil 100% reproducible.
    """
    spec = get_symbol(symbol)
    rng = np.random.default_rng(seed)
    step_min = timeframe_minutes(timeframe)
    idx = pd.date_range(start=start, periods=n, freq=f"{step_min}min", tz="UTC")

    # Return log per bar -> harga close.
    rets = rng.normal(loc=drift, scale=vol, size=n)
    close = start_price * np.exp(np.cumsum(rets))
    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]

    # High/low di sekitar open-close + noise wick.
    wick = np.abs(rng.normal(0.0, vol * 0.6, size=n)) * start_price
    hi = np.maximum(open_, close) + wick
    lo = np.minimum(open_, close) - wick
    vol_series = rng.integers(50, 500, size=n).astype(float)

    df = pd.DataFrame(
        {"open": open_, "high": hi, "low": lo, "close": close, "volume": vol_series},
        index=idx,
    ).round(spec.digits)
    return Bars(symbol=symbol.upper(), timeframe=timeframe, df=df)
