import numpy as np
import pytest

from diel_engine.data.loaders import synthetic_bars
from diel_engine.verification.overfit import pbo_cscv, robust_fraction
from diel_engine.verification.params import apply_overrides, expand_grid, get_grid
from diel_engine.verification.report import (
    BADGE_BACKTESTED, BADGE_ROBUST, BADGE_UNVERIFIED,
)
from diel_engine.verification.splits import (
    time_slices, train_test_split, walk_forward_folds,
)
from diel_engine.verification.verify import verify_strategy

BASE = {
    "name": "ema_cross_v", "symbol": "EURUSD", "timeframe": "H1",
    "indicators": [
        {"id": "ema_fast", "type": "EMA", "period": 20},
        {"id": "ema_slow", "type": "EMA", "period": 50},
    ],
    "entry_long": "cross_over(ema_fast, ema_slow)",
    "entry_short": "cross_under(ema_fast, ema_slow)",
    "exit_long": "cross_under(ema_fast, ema_slow)",
    "exit_short": "cross_over(ema_fast, ema_slow)",
    "stop_loss": {"type": "atr", "mult": 2.0, "atr_period": 14},
    "take_profit": {"type": "rr", "ratio": 1.5},
    "risk": {"per_trade_pct": 1.0},
    "param_grid": {
        "indicators.ema_fast.period": [10, 20],
        "stop_loss.mult": [1.5, 2.5],
    },
}


# ---- splits ----

def test_train_test_split_chronological():
    bars = synthetic_bars("EURUSD", "H1", n=1000, seed=1)
    is_b, oos_b = train_test_split(bars, oos_ratio=0.3)
    assert len(is_b) + len(oos_b) == len(bars)
    # OOS harus di akhir (lebih baru) dari IS.
    assert oos_b.index[0] > is_b.index[-1]
    assert abs(len(oos_b) / len(bars) - 0.3) < 0.01


def test_walk_forward_folds_anchored_grows():
    bars = synthetic_bars("EURUSD", "H1", n=1100, seed=1)
    folds = walk_forward_folds(bars, n_folds=4, anchored=True)
    assert len(folds) == 4
    is_lengths = [len(is_b) for is_b, _ in folds]
    assert is_lengths == sorted(is_lengths)  # IS tumbuh tiap fold


def test_time_slices_cover_all():
    bars = synthetic_bars("EURUSD", "H1", n=800, seed=1)
    slices = time_slices(bars, n_slices=8)
    assert len(slices) == 8
    assert sum(len(s) for s in slices) == len(bars)


# ---- params ----

def test_apply_overrides_indicator_and_nested():
    out = apply_overrides(BASE, {
        "indicators.ema_fast.period": 5,
        "stop_loss.mult": 3.0,
    })
    fast = [i for i in out["indicators"] if i["id"] == "ema_fast"][0]
    assert fast["period"] == 5
    assert out["stop_loss"]["mult"] == 3.0
    # base tidak termutasi
    base_fast = [i for i in BASE["indicators"] if i["id"] == "ema_fast"][0]
    assert base_fast["period"] == 20


def test_expand_grid_cartesian():
    grid = {"a": [1, 2], "b": [10, 20, 30]}
    combos = expand_grid(grid)
    assert len(combos) == 6
    assert {"a": 1, "b": 10} in combos


def test_get_grid_from_spec():
    assert "stop_loss.mult" in get_grid(BASE)


# ---- overfit ----

def test_pbo_zero_when_one_config_dominates():
    # config 0 selalu terbaik di tiap slice -> tidak overfit -> PBO rendah.
    S, N = 8, 4
    M = np.tile(np.array([10.0, 1.0, 0.5, 0.1]), (S, 1))
    M += np.random.default_rng(0).normal(0, 0.01, (S, N))
    pbo, detail = pbo_cscv(M)
    assert pbo == 0.0
    assert detail["n_configs"] == N


def test_pbo_nan_with_single_config():
    pbo, _ = pbo_cscv(np.ones((8, 1)))
    assert np.isnan(pbo)


def test_robust_fraction():
    assert robust_fraction([1.0, -1.0, 2.0, -0.5]) == 0.5
    assert robust_fraction([]) == 0.0


# ---- end to end ----

def test_verify_runs_and_deterministic():
    bars = synthetic_bars("EURUSD", "H1", n=4000, seed=7)
    r1 = verify_strategy(bars, BASE, n_folds=3, n_slices=6)
    r2 = verify_strategy(bars, BASE, n_folds=3, n_slices=6)
    assert r1.score == r2.score
    assert r1.badge == r2.badge
    assert 0.0 <= r1.score <= 100.0
    assert r1.badge in {BADGE_UNVERIFIED, BADGE_BACKTESTED, BADGE_ROBUST}
    assert 0.0 <= r1.robust_fraction <= 1.0
    assert r1.n_configs == 4
    # laporan bisa diserialisasi
    d = r1.to_dict()
    assert "walk_forward" in d and "pbo" in d


def test_verify_losing_strategy_not_robust():
    # Strategi trend-following di random-walk seharusnya tidak dapat badge Robust.
    bars = synthetic_bars("EURUSD", "H1", n=4000, seed=7)
    r = verify_strategy(bars, BASE, n_folds=3, n_slices=6)
    assert r.badge != BADGE_ROBUST


def test_verify_invalid_objective():
    bars = synthetic_bars("EURUSD", "H1", n=500, seed=1)
    with pytest.raises(KeyError):
        verify_strategy(bars, BASE, objective="does_not_exist")
