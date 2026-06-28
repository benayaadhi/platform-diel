"""Orkestrator verifikasi: jalankan semua gerbang -> VerificationReport.

Pipeline:
1. Split kronologis IS/OOS (OOS = data terbaru, ditetapkan platform).
2. Optimisasi grid di IS -> pilih konfigurasi terbaik.
3. Uji konfigurasi terbaik di OOS (data unseen).
4. Evaluasi seluruh grid di OOS -> robust_fraction.
5. Matriks performa per slice -> PBO (CSCV).
6. Walk-forward lintas fold -> consistency & efficiency.
7. Skor 0..100 + badge.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from ..backtest.costs import CostModel
from ..data.models import Bars
from .optimize import OBJECTIVES, evaluate_config, grid_search
from .overfit import pbo_cscv, robust_fraction
from .params import expand_grid, get_grid
from .report import VerificationReport, compute_badge, compute_score
from .splits import time_slices, train_test_split
from .walkforward import walk_forward


def verify_strategy(
    bars: Bars,
    base_spec_dict: Dict[str, Any],
    *,
    grid: Optional[Dict[str, List[Any]]] = None,
    objective: str = "cagr_mdd",
    oos_ratio: float = 0.3,
    n_folds: int = 4,
    n_slices: int = 8,
    initial_balance: float = 10_000.0,
    costs: Optional[CostModel] = None,
    min_oos_trades: int = 20,
) -> VerificationReport:
    if objective not in OBJECTIVES:
        raise KeyError(f"Objektif tidak dikenal: {objective}")
    grid = grid if grid is not None else get_grid(base_spec_dict)
    configs = expand_grid(grid)
    notes: List[str] = []

    # 1-2. Split + optimisasi di IS.
    is_bars, oos_bars = train_test_split(bars, oos_ratio=oos_ratio)
    is_ranked = grid_search(is_bars, base_spec_dict, configs, objective,
                            initial_balance=initial_balance, costs=costs)
    best = is_ranked[0]

    # 3. Uji terbaik di OOS.
    oos_best = evaluate_config(oos_bars, base_spec_dict, best.overrides, objective,
                               initial_balance=initial_balance, costs=costs)

    # 4. Robust fraction: seluruh grid di OOS.
    if len(configs) > 1:
        oos_all = grid_search(oos_bars, base_spec_dict, configs, objective,
                              initial_balance=initial_balance, costs=costs, min_trades=1)
        rf = robust_fraction([c.score for c in oos_all])
    else:
        rf = 1.0 if oos_best.score > 0 else 0.0
        notes.append("robust_fraction trivial (grid 1 konfigurasi)")

    # 5. PBO via CSCV (butuh >=2 konfigurasi & cukup data).
    pbo, pbo_detail = float("nan"), {"reason": "tidak dihitung"}
    if len(configs) > 1:
        try:
            slices = time_slices(bars, n_slices=n_slices)
            M = np.array([
                [evaluate_config(sl, base_spec_dict, ov, objective,
                                 initial_balance=initial_balance, costs=costs).score
                 for ov in configs]
                for sl in slices
            ], dtype=float)
            pbo, pbo_detail = pbo_cscv(M)
        except ValueError as e:
            notes.append(f"PBO dilewati: {e}")
    else:
        notes.append("PBO butuh >= 2 konfigurasi (grid tunggal)")

    # 6. Walk-forward.
    try:
        wf = walk_forward(bars, base_spec_dict, configs, n_folds=n_folds,
                          objective=objective, initial_balance=initial_balance, costs=costs)
    except ValueError as e:
        from .walkforward import WalkForwardSummary
        wf = WalkForwardSummary([], 0.0, 0.0, 0.0)
        notes.append(f"Walk-forward dilewati: {e}")

    # 7. Skor + badge.
    score = compute_score(oos_best.metrics, wf, pbo, rf)
    badge = compute_badge(oos_best.metrics, wf, pbo, score, min_oos_trades=min_oos_trades)
    if oos_best.metrics.get("num_trades", 0) < min_oos_trades:
        notes.append(f"OOS trades < {min_oos_trades}: bukti tak cukup untuk badge")

    return VerificationReport(
        strategy_name=base_spec_dict.get("name", "unnamed"),
        symbol=bars.symbol, timeframe=bars.timeframe,
        objective=objective, n_configs=len(configs),
        best_overrides=best.overrides,
        is_metrics=best.metrics, oos_metrics=oos_best.metrics,
        walk_forward=wf, pbo=pbo, pbo_detail=pbo_detail,
        robust_fraction=rf, score=score, badge=badge, notes=notes,
    )
