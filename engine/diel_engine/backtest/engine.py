"""Engine backtest event-loop untuk forex.

Prinsip korektnes:
- NEXT-BAR EXECUTION: sinyal dihitung pada close bar i, order terisi di open bar
  i+1. Ini menghilangkan look-ahead bias (kita tak bisa transaksi di harga yang
  baru diketahui di akhir bar yang sama).
- SL/TP dicek intrabar memakai high/low. Bila SL & TP sama-sama tersentuh dalam
  satu bar, diasumsikan SL lebih dulu (konservatif).
- Biaya forex (spread, commission, swap) dimodelkan eksplisit (lihat costs.py).
- Position sizing berbasis risiko: % equity dirisiko per trade dari jarak stop.

Output: BacktestResult (metrik + equity curve + daftar trade), deterministik.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..data.models import Bars, SymbolSpec, get_symbol
from ..strategy import indicators as ind
from ..strategy.evaluator import Condition
from ..strategy.spec import ExitSpec, StrategySpec
from .costs import CostModel
from .metrics import compute_metrics
from .results import BacktestResult, Trade


def build_indicators(spec: StrategySpec, bars: Bars) -> Dict[str, np.ndarray]:
    """Hitung semua indikator + sediakan series harga sebagai konteks evaluator."""
    ctx: Dict[str, np.ndarray] = {
        "open": bars.series("open"),
        "high": bars.series("high"),
        "low": bars.series("low"),
        "close": bars.series("close"),
        "volume": bars.series("volume"),
    }
    for ispec in spec.indicators:
        t = ispec.type
        if t == "EMA":
            ctx[ispec.id] = ind.ema(ctx[ispec.source], ispec.period)
        elif t == "SMA":
            ctx[ispec.id] = ind.sma(ctx[ispec.source], ispec.period)
        elif t == "RSI":
            ctx[ispec.id] = ind.rsi(ctx[ispec.source], ispec.period)
        elif t == "ATR":
            ctx[ispec.id] = ind.atr(ctx["high"], ctx["low"], ctx["close"], ispec.period)
        else:
            raise ValueError(f"Tipe indikator tidak didukung: {t}")
    return ctx


def _warmup(spec: StrategySpec) -> int:
    periods = [i.period for i in spec.indicators]
    for ex in (spec.stop_loss, spec.take_profit):
        if ex and ex.type == "atr":
            periods.append(ex.atr_period)
    return (max(periods) if periods else 1) + 1


def _round_lot(lots: float, step: float, lo: float, hi: float) -> float:
    lots = round(lots / step) * step
    return float(min(max(lots, lo), hi))


def _count_nights(entry: pd.Timestamp, exit_: pd.Timestamp):
    """(nights, wednesday_triples) — jumlah midnight UTC yang dilewati posisi.

    Aproksimasi Fase 0: rollover dianggap di midnight UTC; malam Rabu dihitung 3x.
    Model swap broker yang presisi (rollover 22:00 GMT, dst.) menyusul.
    """
    d0 = entry.normalize()
    d1 = exit_.normalize()
    nights = int((d1 - d0).days)
    if nights <= 0:
        return 0, 0
    wed = 0
    for k in range(1, nights + 1):
        if (d0 + pd.Timedelta(days=k)).weekday() == 2:  # Wednesday
            wed += 1
    return nights, wed


class _Position:
    __slots__ = ("direction", "entry_time", "entry_price", "lots",
                 "sl", "tp", "entry_bar", "commission_entry")

    def __init__(self, direction, entry_time, entry_price, lots, sl, tp,
                 entry_bar, commission_entry):
        self.direction = direction
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.lots = lots
        self.sl = sl
        self.tp = tp
        self.entry_bar = entry_bar
        self.commission_entry = commission_entry


def _stop_distance(ex: ExitSpec, atr_val: float, spec_sym: SymbolSpec) -> float:
    if ex.type == "atr":
        if atr_val is None or np.isnan(atr_val) or ex.mult is None:
            return float("nan")
        return ex.mult * atr_val
    if ex.type == "pips":
        return (ex.pips or 0.0) * spec_sym.pip_size
    raise ValueError(f"Tipe stop tidak didukung: {ex.type}")


def run_backtest(
    bars: Bars,
    spec: StrategySpec,
    *,
    initial_balance: float = 10_000.0,
    costs: Optional[CostModel] = None,
) -> BacktestResult:
    costs = costs or CostModel()
    sym = get_symbol(bars.symbol)
    ctx = build_indicators(spec, bars)

    open_ = ctx["open"]; high = ctx["high"]; low = ctx["low"]; close = ctx["close"]
    n = len(bars)
    times = bars.index

    cond_entry_long = Condition(spec.entry_long) if spec.entry_long else None
    cond_entry_short = Condition(spec.entry_short) if spec.entry_short else None
    cond_exit_long = Condition(spec.exit_long) if spec.exit_long else None
    cond_exit_short = Condition(spec.exit_short) if spec.exit_short else None

    # ATR untuk sizing/SL (kalau dipakai).
    atr_series = None
    if spec.stop_loss and spec.stop_loss.type == "atr":
        atr_series = ind.atr(high, low, close, spec.stop_loss.atr_period)

    spread = costs.spread_price(sym)
    slip = costs.slippage_price(sym)

    balance = float(initial_balance)
    pos: Optional[_Position] = None
    pending_entry: Optional[int] = None   # arah entry untuk diisi di open bar berikut
    pending_entry_atr: float = float("nan")
    pending_exit = False                  # exit by signal untuk diisi di open bar berikut

    trades: List[Trade] = []
    equity_vals = np.empty(n, dtype=float)
    equity_vals[:] = balance
    bars_in_market = 0

    start = _warmup(spec)

    def price_pnl(p: _Position, exit_price: float) -> float:
        return p.direction * (exit_price - p.entry_price) * sym.contract_size * p.lots

    def close_position(p: _Position, exit_price: float, exit_time, exit_bar: int,
                       reason: str) -> None:
        nonlocal balance, pos
        gross = price_pnl(p, exit_price)
        comm_exit = costs.commission_cost(p.lots)
        nights, wed = _count_nights(p.entry_time, exit_time)
        swap = costs.swap_cost(p.direction, p.lots, nights, wed, sym)
        net = gross - p.commission_entry - comm_exit + swap
        balance += gross - comm_exit + swap  # entry commission sudah dipotong saat entry
        trades.append(Trade(
            direction=p.direction, entry_time=p.entry_time, exit_time=exit_time,
            entry_price=p.entry_price, exit_price=exit_price, lots=p.lots,
            stop_loss=p.sl, take_profit=p.tp, gross_pnl=gross,
            commission=p.commission_entry + comm_exit, swap=swap, net_pnl=net,
            exit_reason=reason, bars_held=exit_bar - p.entry_bar,
            equity_after=balance,
        ))
        pos = None

    for i in range(n):
        # --- (A) Exit by signal: isi di open bar ini ---
        if pos is not None and pending_exit:
            fill = open_[i] - slip if pos.direction > 0 else open_[i] + slip
            close_position(pos, fill, times[i], i, "signal")
            pending_exit = False

        # --- (B) Entry tertunda: isi di open bar ini ---
        if pos is None and pending_entry is not None and i >= 1:
            direction = pending_entry
            if direction > 0:
                fill = open_[i] + spread + slip
            else:
                fill = open_[i] - spread - slip

            sl_price = float("nan"); tp_price = float("nan"); lots = spec.risk.min_lot
            if spec.stop_loss is not None:
                sl_dist = _stop_distance(spec.stop_loss, pending_entry_atr, sym)
                if not np.isnan(sl_dist) and sl_dist > 0:
                    sl_price = fill - sl_dist if direction > 0 else fill + sl_dist
                    risk_amt = balance * spec.risk.per_trade_pct / 100.0
                    pip_dist = sl_dist / sym.pip_size
                    raw_lots = risk_amt / (pip_dist * sym.pip_value_per_lot)
                    lots = _round_lot(raw_lots, spec.risk.lot_step,
                                      spec.risk.min_lot, spec.risk.max_lot)
                    if spec.take_profit is not None:
                        if spec.take_profit.type == "rr" and spec.take_profit.ratio:
                            tp_dist = spec.take_profit.ratio * sl_dist
                        elif spec.take_profit.type == "pips":
                            tp_dist = (spec.take_profit.pips or 0.0) * sym.pip_size
                        else:
                            tp_dist = 0.0
                        if tp_dist > 0:
                            tp_price = (fill + tp_dist if direction > 0
                                        else fill - tp_dist)
            if lots > 0:
                comm_entry = costs.commission_cost(lots)
                balance -= comm_entry
                pos = _Position(direction, times[i], fill, lots, sl_price, tp_price,
                                i, comm_entry)
            pending_entry = None
            pending_entry_atr = float("nan")

        # --- (C) Kelola posisi: cek SL/TP intrabar bar ini ---
        if pos is not None:
            if pos.direction > 0:
                hit_sl = not np.isnan(pos.sl) and low[i] <= pos.sl
                hit_tp = not np.isnan(pos.tp) and high[i] >= pos.tp
            else:
                hit_sl = not np.isnan(pos.sl) and high[i] >= pos.sl
                hit_tp = not np.isnan(pos.tp) and low[i] <= pos.tp
            if hit_sl:  # konservatif: SL didahulukan bila keduanya kena
                close_position(pos, pos.sl, times[i], i, "sl")
            elif hit_tp:
                close_position(pos, pos.tp, times[i], i, "tp")

        # --- (D) Sinyal exit di close bar ini -> isi bar berikutnya ---
        if pos is not None and i >= start:
            if pos.direction > 0 and cond_exit_long and cond_exit_long.eval(ctx, i):
                pending_exit = True
            elif pos.direction < 0 and cond_exit_short and cond_exit_short.eval(ctx, i):
                pending_exit = True

        # --- (E) Sinyal entry di close bar ini -> isi bar berikutnya ---
        if pos is None and pending_entry is None and i >= start:
            if cond_entry_long and cond_entry_long.eval(ctx, i):
                pending_entry = 1
            elif cond_entry_short and cond_entry_short.eval(ctx, i):
                pending_entry = -1
            if pending_entry is not None and atr_series is not None:
                pending_entry_atr = float(atr_series[i])

        # --- Mark-to-market equity di close bar ini ---
        if pos is not None:
            equity_vals[i] = balance + price_pnl(pos, close[i])
            bars_in_market += 1
        else:
            equity_vals[i] = balance

    # Tutup posisi tersisa di akhir data.
    if pos is not None:
        close_position(pos, close[n - 1], times[n - 1], n - 1, "eod")
        equity_vals[n - 1] = balance

    equity = pd.Series(equity_vals, index=times, name="equity")
    metrics = compute_metrics(
        equity, trades, initial_balance,
        bars_in_market=bars_in_market, total_bars=n,
    )
    return BacktestResult(
        symbol=bars.symbol, timeframe=bars.timeframe, strategy_name=spec.name,
        initial_balance=initial_balance, final_equity=float(equity.iloc[-1]),
        trades=trades, equity_curve=equity, metrics=metrics,
        cost_assumptions={
            "spread_pips": costs.spread_pips,
            "commission_per_lot": costs.commission_per_lot,
            "swap_long_pips": costs.swap_long_pips,
            "swap_short_pips": costs.swap_short_pips,
            "slippage_pips": costs.slippage_pips,
        },
    )
