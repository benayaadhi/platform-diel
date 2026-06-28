"""Struktur hasil backtest: trade, equity curve, dan BacktestResult agregat."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

import pandas as pd


@dataclass
class Trade:
    direction: int            # +1 long, -1 short
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    lots: float
    stop_loss: float
    take_profit: float
    gross_pnl: float          # P&L harga * size, sebelum biaya
    commission: float
    swap: float
    net_pnl: float            # gross - commission - swap
    exit_reason: str          # 'sl' | 'tp' | 'signal' | 'eod'
    bars_held: int
    equity_after: float

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["entry_time"] = self.entry_time.isoformat()
        d["exit_time"] = self.exit_time.isoformat()
        return d


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    strategy_name: str
    initial_balance: float
    final_equity: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    metrics: Dict[str, float] = field(default_factory=dict)
    cost_assumptions: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        m = self.metrics
        lines = [
            f"Strategy : {self.strategy_name}  ({self.symbol} {self.timeframe})",
            f"Balance  : {self.initial_balance:,.2f} -> {self.final_equity:,.2f}",
            f"Trades   : {int(m.get('num_trades', 0))}  "
            f"(win {m.get('win_rate', 0)*100:.1f}%)",
            f"Net PnL  : {m.get('net_pnl', 0):,.2f}  "
            f"({m.get('total_return', 0)*100:.2f}%)",
            f"CAGR     : {m.get('cagr', 0)*100:.2f}%",
            f"MaxDD    : {m.get('max_drawdown', 0)*100:.2f}%",
            f"Sharpe   : {m.get('sharpe', 0):.2f}   Sortino: {m.get('sortino', 0):.2f}",
            f"ProfitF  : {m.get('profit_factor', 0):.2f}   "
            f"Expectancy: {m.get('expectancy', 0):,.2f}",
            f"Recovery : {m.get('recovery_factor', 0):.2f}   "
            f"Exposure: {m.get('exposure', 0)*100:.1f}%",
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy_name": self.strategy_name,
            "initial_balance": self.initial_balance,
            "final_equity": self.final_equity,
            "metrics": self.metrics,
            "cost_assumptions": self.cost_assumptions,
            "trades": [t.to_dict() for t in self.trades],
        }
