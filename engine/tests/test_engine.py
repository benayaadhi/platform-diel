import numpy as np
import pandas as pd
import pytest

from diel_engine.backtest.costs import CostModel
from diel_engine.backtest.engine import run_backtest
from diel_engine.data.loaders import synthetic_bars
from diel_engine.data.models import Bars
from diel_engine.strategy.spec import load_spec, spec_from_dict

EMA_SPEC = {
    "name": "ema_cross_test", "symbol": "EURUSD", "timeframe": "H1",
    "indicators": [
        {"id": "ema_fast", "type": "EMA", "period": 10},
        {"id": "ema_slow", "type": "EMA", "period": 30},
    ],
    "entry_long": "cross_over(ema_fast, ema_slow)",
    "entry_short": "cross_under(ema_fast, ema_slow)",
    "exit_long": "cross_under(ema_fast, ema_slow)",
    "exit_short": "cross_over(ema_fast, ema_slow)",
    "stop_loss": {"type": "atr", "mult": 2.0, "atr_period": 14},
    "take_profit": {"type": "rr", "ratio": 1.5},
    "risk": {"per_trade_pct": 1.0},
}


def test_end_to_end_runs_and_is_deterministic():
    spec = spec_from_dict(EMA_SPEC)
    bars = synthetic_bars("EURUSD", "H1", n=3000, seed=7)
    r1 = run_backtest(bars, spec)
    r2 = run_backtest(bars, spec)
    assert r1.final_equity == r2.final_equity
    assert r1.metrics["num_trades"] == r2.metrics["num_trades"]
    assert len(r1.equity_curve) == len(bars)
    # Harus menghasilkan setidaknya beberapa trade pada 3000 bar.
    assert r1.metrics["num_trades"] > 0


def test_equity_curve_aligned_to_bars():
    spec = spec_from_dict(EMA_SPEC)
    bars = synthetic_bars("EURUSD", "H1", n=1000, seed=1)
    r = run_backtest(bars, spec)
    assert list(r.equity_curve.index) == list(bars.index)
    assert r.equity_curve.iloc[0] == pytest.approx(10_000.0)


def test_costs_reduce_returns():
    """Spread/komisi lebih tinggi tidak boleh menaikkan profit (no free lunch)."""
    spec = spec_from_dict(EMA_SPEC)
    bars = synthetic_bars("EURUSD", "H1", n=3000, seed=3)
    cheap = run_backtest(bars, spec, costs=CostModel(spread_pips=0.0, commission_per_lot=0.0,
                                                     swap_long_pips=0.0, swap_short_pips=0.0))
    pricey = run_backtest(bars, spec, costs=CostModel(spread_pips=3.0, commission_per_lot=7.0,
                                                      swap_long_pips=-2.0, swap_short_pips=-2.0))
    assert pricey.final_equity < cheap.final_equity


def test_sl_respected_no_extreme_loss_per_trade():
    """Tiap trade rugi tak boleh jauh melebihi risiko yang ditetapkan (+buffer biaya).

    risk per trade = 1% dari ~10k = ~100; beri buffer untuk slippage gap/biaya.
    """
    spec = spec_from_dict(EMA_SPEC)
    bars = synthetic_bars("EURUSD", "H1", n=4000, seed=11)
    r = run_backtest(bars, spec)
    for t in r.trades:
        if t.exit_reason == "sl":
            # rugi bersih SL tidak boleh > ~3x risiko (toleransi gap intrabar + biaya)
            assert t.net_pnl > -350, f"SL loss terlalu besar: {t.net_pnl}"


def test_no_lookahead_uses_next_bar_open():
    """Entry harus terisi di OPEN bar setelah sinyal, bukan di close bar sinyal."""
    spec = spec_from_dict(EMA_SPEC)
    bars = synthetic_bars("EURUSD", "H1", n=2000, seed=5)
    r = run_backtest(bars, spec)
    closes = bars.df["close"].to_numpy()
    opens = bars.df["open"].to_numpy()
    idx = {ts: k for k, ts in enumerate(bars.index)}
    for t in r.trades:
        k = idx[t.entry_time]
        # entry price dekat ke open[k] (plus spread/slippage), bukan ke close[k-1]
        assert abs(t.entry_price - opens[k]) < abs(t.entry_price - closes[k - 1]) + 1e-9


def test_example_spec_loads():
    import os
    here = os.path.dirname(os.path.dirname(__file__))
    spec = load_spec(os.path.join(here, "examples", "ema_cross.json"))
    assert spec.symbol == "EURUSD"
    assert len(spec.indicators) == 2


def test_bars_validation_rejects_missing_columns():
    df = pd.DataFrame({"open": [1.0], "high": [1.0], "low": [1.0]},
                      index=pd.DatetimeIndex(["2020-01-01"], tz="UTC"))
    with pytest.raises(ValueError):
        Bars("EURUSD", "H1", df)
