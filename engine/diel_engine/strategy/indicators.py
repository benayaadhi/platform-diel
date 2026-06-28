"""Indikator teknikal vektor (numpy).

Semua fungsi mengembalikan array sepanjang input dengan NaN di periode warmup,
sehingga index tetap selaras dengan bars. Tidak ada look-ahead: nilai pada
index i hanya memakai data <= i.
"""
from __future__ import annotations

import numpy as np


def sma(x: np.ndarray, period: int) -> np.ndarray:
    if period < 1:
        raise ValueError("period harus >= 1")
    out = np.full_like(x, np.nan, dtype=float)
    if len(x) < period:
        return out
    csum = np.cumsum(np.insert(x, 0, 0.0))
    out[period - 1:] = (csum[period:] - csum[:-period]) / period
    return out


def ema(x: np.ndarray, period: int) -> np.ndarray:
    if period < 1:
        raise ValueError("period harus >= 1")
    out = np.full_like(x, np.nan, dtype=float)
    if len(x) < period:
        return out
    alpha = 2.0 / (period + 1.0)
    # Seed dengan SMA periode pertama (konvensi umum), lalu rekursif.
    seed = np.mean(x[:period])
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(x)):
        prev = alpha * x[i] + (1.0 - alpha) * prev
        out[i] = prev
    return out


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]
    a = high - low
    b = np.abs(high - prev_close)
    c = np.abs(low - prev_close)
    tr = np.maximum.reduce([a, b, c])
    tr[0] = high[0] - low[0]
    return tr


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """ATR dengan smoothing Wilder (RMA)."""
    tr = true_range(high, low, close)
    out = np.full_like(close, np.nan, dtype=float)
    if len(close) < period:
        return out
    seed = np.mean(tr[:period])
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(close)):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    return out


def rsi(x: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    if len(x) <= period:
        return out
    delta = np.diff(x)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])
    for i in range(period, len(x)):
        g = gain[i - 1]
        l = loss[i - 1]
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else np.inf
        out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out
