"""Perhitungan metrik performa dari equity curve + daftar trade.

Catatan kejujuran statistik (lihat BLUEPRINT §6): metrik in-sample saja TIDAK
cukup untuk badge. Modul ini menghitung angka mentah; gerbang verifikasi
(OOS/walk-forward/overfit) dibangun di Fase 1 di atas fondasi ini.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import pandas as pd

from .results import Trade

_MINUTES_PER_YEAR = 365.0 * 24 * 60


def _bars_per_year(equity: pd.Series) -> float:
    if len(equity.index) < 3:
        return 252.0
    deltas = np.diff(equity.index.view("int64")) / 1e9 / 60.0  # menit antar bar
    step = float(np.median(deltas))
    if step <= 0:
        return 252.0
    return _MINUTES_PER_YEAR / step


def compute_metrics(
    equity: pd.Series,
    trades: List[Trade],
    initial_balance: float,
    *,
    bars_in_market: int = 0,
    total_bars: int = 0,
) -> Dict[str, float]:
    m: Dict[str, float] = {}
    final = float(equity.iloc[-1]) if len(equity) else initial_balance
    net_pnl = final - initial_balance
    m["net_pnl"] = net_pnl
    m["total_return"] = net_pnl / initial_balance if initial_balance else 0.0

    # CAGR berbasis durasi kalender.
    if len(equity) >= 2:
        secs = (equity.index[-1] - equity.index[0]).total_seconds()
        years = secs / (365.0 * 24 * 3600)
    else:
        years = 0.0
    if years > 0 and final > 0 and initial_balance > 0:
        m["cagr"] = (final / initial_balance) ** (1.0 / years) - 1.0
    else:
        m["cagr"] = 0.0

    # Max drawdown dari equity curve.
    if len(equity):
        running_max = equity.cummax()
        dd = (equity - running_max) / running_max
        m["max_drawdown"] = float(dd.min())  # negatif
    else:
        m["max_drawdown"] = 0.0

    # Sharpe & Sortino tahunan dari return per-bar.
    rets = equity.pct_change().dropna().to_numpy()
    bpy = _bars_per_year(equity)
    if len(rets) > 1 and rets.std(ddof=1) > 0:
        m["sharpe"] = float(rets.mean() / rets.std(ddof=1) * math.sqrt(bpy))
    else:
        m["sharpe"] = 0.0
    downside = rets[rets < 0]
    if len(downside) > 1 and downside.std(ddof=1) > 0:
        m["sortino"] = float(rets.mean() / downside.std(ddof=1) * math.sqrt(bpy))
    else:
        m["sortino"] = 0.0

    # Statistik level-trade.
    pnls = np.array([t.net_pnl for t in trades], dtype=float)
    m["num_trades"] = float(len(trades))
    if len(pnls):
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        m["win_rate"] = float(len(wins) / len(pnls))
        gross_win = float(wins.sum())
        gross_loss = float(-losses.sum())
        m["profit_factor"] = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
        m["expectancy"] = float(pnls.mean())
        m["avg_win"] = float(wins.mean()) if len(wins) else 0.0
        m["avg_loss"] = float(losses.mean()) if len(losses) else 0.0
    else:
        m.update(win_rate=0.0, profit_factor=0.0, expectancy=0.0,
                 avg_win=0.0, avg_loss=0.0)

    # Recovery factor = net profit / max drawdown absolut (mata uang).
    if len(equity):
        peak = equity.cummax()
        dd_abs = float((peak - equity).max())
        m["recovery_factor"] = (net_pnl / dd_abs) if dd_abs > 0 else 0.0
    else:
        m["recovery_factor"] = 0.0

    m["exposure"] = (bars_in_market / total_bars) if total_bars else 0.0
    return m
