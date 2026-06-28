"""Optimisasi / evaluasi grid konfigurasi pada satu segmen data.

Objektif default = CAGR / |MaxDD| (return relatif terhadap risiko), bukan profit
mentah — lebih tahan terhadap strategi yang "profit tapi drawdown ngeri".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..backtest.costs import CostModel
from ..backtest.engine import run_backtest
from ..data.models import Bars
from ..strategy.spec import spec_from_dict
from .params import apply_overrides


def _cagr_mdd(m: Dict[str, float]) -> float:
    dd = abs(m.get("max_drawdown", 0.0))
    if dd < 1e-9:
        return m.get("cagr", 0.0) * 10.0  # tanpa drawdown: hadiahi, hindari /0
    return m.get("cagr", 0.0) / dd


def _profit_factor(m: Dict[str, float]) -> float:
    pf = m.get("profit_factor", 0.0)
    return min(pf, 100.0)  # cap inf


OBJECTIVES: Dict[str, Callable[[Dict[str, float]], float]] = {
    "cagr_mdd": _cagr_mdd,
    "sharpe": lambda m: m.get("sharpe", 0.0),
    "sortino": lambda m: m.get("sortino", 0.0),
    "profit_factor": _profit_factor,
    "net_pnl": lambda m: m.get("net_pnl", 0.0),
    "total_return": lambda m: m.get("total_return", 0.0),
    "expectancy": lambda m: m.get("expectancy", 0.0),
}


@dataclass
class ConfigResult:
    overrides: Dict[str, Any]
    metrics: Dict[str, float]
    score: float


def evaluate_config(
    bars: Bars,
    base_spec_dict: Dict[str, Any],
    overrides: Dict[str, Any],
    objective: str = "cagr_mdd",
    *,
    initial_balance: float = 10_000.0,
    costs: Optional[CostModel] = None,
) -> ConfigResult:
    spec = spec_from_dict(apply_overrides(base_spec_dict, overrides))
    result = run_backtest(bars, spec, initial_balance=initial_balance, costs=costs)
    score = OBJECTIVES[objective](result.metrics)
    return ConfigResult(overrides=overrides, metrics=result.metrics, score=score)


def grid_search(
    bars: Bars,
    base_spec_dict: Dict[str, Any],
    configs: List[Dict[str, Any]],
    objective: str = "cagr_mdd",
    *,
    initial_balance: float = 10_000.0,
    costs: Optional[CostModel] = None,
    min_trades: int = 5,
) -> List[ConfigResult]:
    """Evaluasi semua konfigurasi, terurut skor menurun.

    Konfigurasi dengan trade < min_trades di-skor sangat rendah (tidak cukup bukti).
    """
    if objective not in OBJECTIVES:
        raise KeyError(f"Objektif tidak dikenal: {objective}")
    results: List[ConfigResult] = []
    for ov in configs:
        r = evaluate_config(bars, base_spec_dict, ov, objective,
                            initial_balance=initial_balance, costs=costs)
        if r.metrics.get("num_trades", 0) < min_trades:
            r = ConfigResult(ov, r.metrics, -1e9)
        results.append(r)
    results.sort(key=lambda c: c.score, reverse=True)
    return results
