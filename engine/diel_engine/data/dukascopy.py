"""Ingester data tick Dukascopy (sumber forex historis gratis & berkualitas).

Dukascopy menyimpan tick per-jam dalam file .bi5 (LZMA) di:
  https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YYYY}/{MM0:02d}/{DD:02d}/{HH:02d}h_ticks.bi5
dengan MM0 = bulan berbasis-0 (Januari = 00).

Tiap record = 20 byte big-endian:
  uint32  ms offset dari awal jam
  int32   ask (dalam point, skala 10**digits)
  int32   bid (dalam point)
  float32 ask volume
  float32 bid volume

Modul ini BUTUH jaringan. Untuk demo/test offline pakai loaders.synthetic_bars.
Output diselaraskan menjadi objek Bars yang sama seperti loader lain, sehingga
engine tidak perlu tahu sumbernya.
"""
from __future__ import annotations

import datetime as dt
import lzma
import struct
import urllib.request
from typing import List, Tuple

import numpy as np
import pandas as pd

from .loaders import timeframe_minutes
from .models import Bars, get_symbol

_BASE = "https://datafeed.dukascopy.com/datafeed"
_REC = struct.Struct(">IIIff")  # 20 byte per tick


def _hour_url(symbol: str, when: dt.datetime) -> str:
    return (
        f"{_BASE}/{symbol.upper()}/{when.year:04d}/{when.month - 1:02d}/"
        f"{when.day:02d}/{when.hour:02d}h_ticks.bi5"
    )


def _fetch_hour_ticks(symbol: str, when: dt.datetime, point: float,
                      timeout: float = 30.0) -> List[Tuple[dt.datetime, float, float]]:
    """Unduh + dekompres satu jam tick. List kosong kalau tidak ada data (mis. weekend)."""
    url = _hour_url(symbol, when)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read()
    except Exception:
        return []
    if not raw:
        return []
    try:
        data = lzma.decompress(raw)
    except lzma.LZMAError:
        return []

    out: List[Tuple[dt.datetime, float, float]] = []
    base = when.replace(minute=0, second=0, microsecond=0)
    for off in range(0, len(data) - _REC.size + 1, _REC.size):
        ms, ask_i, bid_i, _av, _bv = _REC.unpack_from(data, off)
        ts = base + dt.timedelta(milliseconds=ms)
        out.append((ts, ask_i * point, bid_i * point))
    return out


def download_bars(
    symbol: str,
    timeframe: str,
    start: dt.datetime,
    end: dt.datetime,
) -> Bars:
    """Unduh tick rentang [start, end) lalu agregasi ke OHLC sesuai timeframe.

    Harga bar memakai MID = (ask+bid)/2; spread dimodelkan terpisah di engine
    (lihat backtest/costs.py) agar asumsi biaya transparan & bisa diaudit.
    """
    spec = get_symbol(symbol)
    cur = start.replace(minute=0, second=0, microsecond=0)
    rows: List[Tuple[dt.datetime, float]] = []
    while cur < end:
        for ts, ask, bid in _fetch_hour_ticks(symbol, cur, spec.point):
            if start <= ts < end:
                rows.append((ts, (ask + bid) / 2.0))
        cur += dt.timedelta(hours=1)

    if not rows:
        raise RuntimeError(
            f"Tidak ada tick terunduh untuk {symbol} {start}..{end} "
            "(cek jaringan / rentang weekend)."
        )

    ticks = pd.DataFrame(rows, columns=["ts", "mid"]).set_index("ts")
    ticks.index = pd.DatetimeIndex(ticks.index, tz="UTC")
    rule = f"{timeframe_minutes(timeframe)}min"
    ohlc = ticks["mid"].resample(rule, label="left", closed="left").ohlc().dropna()
    ohlc["volume"] = ticks["mid"].resample(rule, label="left", closed="left").count()
    ohlc = ohlc.round(spec.digits)
    return Bars(symbol=symbol.upper(), timeframe=timeframe, df=ohlc)
