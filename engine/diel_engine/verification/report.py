"""Struktur & ringkasan laporan verifikasi + logika skor/badge."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .walkforward import WalkForwardSummary

# Level badge (BLUEPRINT §6). Forward/Live butuh Fase 4 (forward test demo MT5),
# jadi verifikasi backtest ini maksimal memberi "Robust".
BADGE_UNVERIFIED = "Unverified"
BADGE_BACKTESTED = "Backtested"   # 🟦
BADGE_ROBUST = "Robust"           # 🟩


@dataclass
class VerificationReport:
    strategy_name: str
    symbol: str
    timeframe: str
    objective: str
    n_configs: int
    best_overrides: Dict[str, Any]
    is_metrics: Dict[str, float]
    oos_metrics: Dict[str, float]
    walk_forward: WalkForwardSummary
    pbo: float
    pbo_detail: Dict[str, Any]
    robust_fraction: float
    score: float
    badge: str
    notes: list = field(default_factory=list)

    def summary(self) -> str:
        wf = self.walk_forward
        oos = self.oos_metrics
        lines = [
            f"=== VERIFICATION: {self.strategy_name} ({self.symbol} {self.timeframe}) ===",
            f"Objective       : {self.objective}   Configs tested: {self.n_configs}",
            f"Best params     : {self.best_overrides or '(none)'}",
            "-- In-sample (IS) --",
            f"  return {self.is_metrics.get('total_return',0)*100:6.2f}%   "
            f"trades {int(self.is_metrics.get('num_trades',0))}",
            "-- Out-of-sample (OOS) --",
            f"  return {oos.get('total_return',0)*100:6.2f}%   "
            f"maxDD {oos.get('max_drawdown',0)*100:6.2f}%   "
            f"PF {oos.get('profit_factor',0):.2f}   "
            f"trades {int(oos.get('num_trades',0))}",
            "-- Walk-forward --",
            f"  consistency {wf.consistency*100:5.1f}% folds OOS+   "
            f"efficiency {wf.wf_efficiency:.2f}   "
            f"avg OOS {wf.avg_oos_return*100:.2f}%",
            "-- Overfit checks --",
            f"  PBO {self.pbo:.2f}   robust region {self.robust_fraction*100:.1f}%",
            "-" * 48,
            f"  SCORE {self.score:.1f}/100   ->   BADGE: {self.badge}",
        ]
        if self.notes:
            lines.append("Notes: " + "; ".join(self.notes))
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "objective": self.objective,
            "n_configs": self.n_configs,
            "best_overrides": self.best_overrides,
            "is_metrics": self.is_metrics,
            "oos_metrics": self.oos_metrics,
            "walk_forward": self.walk_forward.to_dict(),
            "pbo": self.pbo,
            "pbo_detail": self.pbo_detail,
            "robust_fraction": self.robust_fraction,
            "score": self.score,
            "badge": self.badge,
            "notes": self.notes,
        }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_score(
    oos_metrics: Dict[str, float],
    wf: WalkForwardSummary,
    pbo: float,
    robust_fraction: float,
) -> float:
    """Skor komposit 0..100. Berbobot ke bukti unseen (OOS + walk-forward)."""
    # Komponen return OOS: 0% -> 0, >=20% -> 1.
    oos_ret = oos_metrics.get("total_return", 0.0)
    oos_component = _clamp01(oos_ret / 0.20)
    wf_component = _clamp01(wf.consistency)
    pbo_component = _clamp01(1.0 - (pbo if pbo == pbo else 1.0))  # NaN -> 0
    robust_component = _clamp01(robust_fraction)
    score = 100.0 * (
        0.35 * oos_component
        + 0.30 * wf_component
        + 0.20 * pbo_component
        + 0.15 * robust_component
    )
    return round(score, 1)


def compute_badge(
    oos_metrics: Dict[str, float],
    wf: WalkForwardSummary,
    pbo: float,
    score: float,
    *,
    min_oos_trades: int = 20,
) -> str:
    if oos_metrics.get("num_trades", 0) < min_oos_trades:
        return BADGE_UNVERIFIED
    if oos_metrics.get("total_return", 0.0) <= 0.0:
        return BADGE_UNVERIFIED
    pbo_ok = (pbo == pbo) and pbo < 0.5  # bukan NaN & < 0.5
    if score >= 70.0 and wf.consistency >= 0.6 and pbo_ok:
        return BADGE_ROBUST
    return BADGE_BACKTESTED
