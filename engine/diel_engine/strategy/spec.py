"""Spec strategi (DSL terstruktur) + parsing/validasi.

Strategi DIDESKRIPSIKAN sebagai data, bukan kode bebas. Ini sengaja:
1) aman (tak ada eksekusi kode user sembarangan),
2) verifiable & reproducible,
3) bisa di-codegen ke MQL5/MQL4/Pine nanti.

Contoh lengkap ada di examples/ema_cross.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IndicatorSpec:
    id: str
    type: str                       # EMA | SMA | ATR | RSI
    period: int
    source: str = "close"           # close|open|high|low (untuk EMA/SMA/RSI)


@dataclass
class ExitSpec:
    """Stop loss / take profit.

    SL types: 'atr' (mult * ATR), 'pips' (jarak tetap pips).
    TP types: 'rr' (ratio * jarak SL), 'pips' (jarak tetap pips).
    """
    type: str
    mult: Optional[float] = None
    ratio: Optional[float] = None
    pips: Optional[float] = None
    atr_period: int = 14


@dataclass
class RiskSpec:
    per_trade_pct: float = 1.0      # % equity dirisiko per trade
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 100.0


@dataclass
class StrategySpec:
    name: str
    symbol: str
    timeframe: str
    indicators: List[IndicatorSpec]
    entry_long: Optional[str] = None
    entry_short: Optional[str] = None
    exit_long: Optional[str] = None
    exit_short: Optional[str] = None
    stop_loss: Optional[ExitSpec] = None
    take_profit: Optional[ExitSpec] = None
    risk: RiskSpec = field(default_factory=RiskSpec)
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.indicators and not (self.entry_long or self.entry_short):
            raise ValueError("Strategi tanpa indikator & tanpa sinyal entry")
        ids = [i.id for i in self.indicators]
        if len(ids) != len(set(ids)):
            raise ValueError("ID indikator harus unik")
        if not (self.entry_long or self.entry_short):
            raise ValueError("Minimal satu dari entry_long/entry_short harus ada")


def _exit_from(d: Optional[Dict[str, Any]]) -> Optional[ExitSpec]:
    if not d:
        return None
    return ExitSpec(
        type=d["type"],
        mult=d.get("mult"),
        ratio=d.get("ratio"),
        pips=d.get("pips"),
        atr_period=d.get("atr_period", 14),
    )


def spec_from_dict(d: Dict[str, Any]) -> StrategySpec:
    indicators = [
        IndicatorSpec(
            id=i["id"], type=i["type"].upper(),
            period=int(i["period"]), source=i.get("source", "close"),
        )
        for i in d.get("indicators", [])
    ]
    risk_d = d.get("risk", {})
    risk = RiskSpec(
        per_trade_pct=float(risk_d.get("per_trade_pct", 1.0)),
        min_lot=float(risk_d.get("min_lot", 0.01)),
        lot_step=float(risk_d.get("lot_step", 0.01)),
        max_lot=float(risk_d.get("max_lot", 100.0)),
    )
    spec = StrategySpec(
        name=d.get("name", "unnamed"),
        symbol=d["symbol"].upper(),
        timeframe=d["timeframe"].upper(),
        indicators=indicators,
        entry_long=d.get("entry_long"),
        entry_short=d.get("entry_short"),
        exit_long=d.get("exit_long"),
        exit_short=d.get("exit_short"),
        stop_loss=_exit_from(d.get("stop_loss")),
        take_profit=_exit_from(d.get("take_profit")),
        risk=risk,
        meta=d.get("meta", {}),
    )
    spec.validate()
    return spec


def load_spec(path: str) -> StrategySpec:
    with open(path, "r", encoding="utf-8") as f:
        return spec_from_dict(json.load(f))
