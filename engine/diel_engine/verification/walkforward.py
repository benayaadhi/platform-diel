"""Walk-forward analysis.

Untuk tiap fold: optimisasi parameter HANYA di in-sample, lalu uji konfigurasi
terpilih di out-of-sample fold itu. Mengukur apakah proses pemilihan strategi
bertahan di data yang belum pernah dilihat — bukan sekadar satu periode beruntung.

Metrik kunci:
- consistency : fraksi fold yang OOS-nya profit.
- wf_efficiency: rata-rata (return OOS / return IS) — <1 berarti performa luruh OOS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from ..backtest.costs import CostModel
from ..data.models import Bars
from .optimize import evaluate_config, grid_search
from .splits import walk_forward_folds


@dataclass
class FoldResult:
    index: int
    is_bars: int
    oos_bars: int
    best_overrides: Dict[str, Any]
    is_return: float
    oos_return: float
    oos_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class WalkForwardSummary:
    folds: List[FoldResult]
    consistency: float
    wf_efficiency: float
    avg_oos_return: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consistency": self.consistency,
            "wf_efficiency": self.wf_efficiency,
            "avg_oos_return": self.avg_oos_return,
            "folds": [
                {
                    "index": f.index, "is_bars": f.is_bars, "oos_bars": f.oos_bars,
                    "best_overrides": f.best_overrides,
                    "is_return": f.is_return, "oos_return": f.oos_return,
                    "oos_trades": f.oos_metrics.get("num_trades", 0),
                }
                for f in self.folds
            ],
        }


def walk_forward(
    bars: Bars,
    base_spec_dict: Dict[str, Any],
    configs: List[Dict[str, Any]],
    *,
    n_folds: int = 4,
    anchored: bool = True,
    objective: str = "cagr_mdd",
    initial_balance: float = 10_000.0,
    costs: Optional[CostModel] = None,
) -> WalkForwardSummary:
    folds = walk_forward_folds(bars, n_folds=n_folds, anchored=anchored)
    results: List[FoldResult] = []
    for i, (is_bars, oos_bars) in enumerate(folds):
        ranked = grid_search(is_bars, base_spec_dict, configs, objective,
                             initial_balance=initial_balance, costs=costs)
        best = ranked[0]
        is_ret = best.metrics.get("total_return", 0.0)
        oos = evaluate_config(oos_bars, base_spec_dict, best.overrides, objective,
                              initial_balance=initial_balance, costs=costs)
        results.append(FoldResult(
            index=i, is_bars=len(is_bars), oos_bars=len(oos_bars),
            best_overrides=best.overrides, is_return=is_ret,
            oos_return=oos.metrics.get("total_return", 0.0),
            oos_metrics=oos.metrics,
        ))

    oos_returns = np.array([f.oos_return for f in results], dtype=float)
    consistency = float(np.mean(oos_returns > 0.0)) if len(oos_returns) else 0.0
    # WFE: rasio return OOS thd IS, hanya untuk fold yang IS-nya profit (>0).
    ratios = [f.oos_return / f.is_return for f in results if f.is_return > 1e-9]
    wfe = float(np.mean(ratios)) if ratios else 0.0
    avg_oos = float(oos_returns.mean()) if len(oos_returns) else 0.0
    return WalkForwardSummary(results, consistency, wfe, avg_oos)
