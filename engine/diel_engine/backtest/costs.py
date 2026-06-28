"""Model biaya trading forex.

Kalau biaya tidak dimodelkan, backtest forex bohong. Yang kita modelkan:
- spread (selisih bid/ask) — dibebankan sekali per round-trip saat entry,
- commission per lot per sisi (entry & exit),
- swap/rollover per malam tahan posisi (triple di hari Rabu — konvensi pasar).

Semua parameter eksplisit & disimpan di hasil agar asumsi transparan/auditable.
Nilai berbeda antar broker; ini default yang masuk akal untuk EURUSD ECN-like.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.models import SymbolSpec


@dataclass(frozen=True)
class CostModel:
    spread_pips: float = 1.0            # spread rata-rata (pips)
    commission_per_lot: float = 3.5     # per lot per sisi (mata uang akun)
    swap_long_pips: float = -0.5        # per malam, long (negatif = biaya)
    swap_short_pips: float = -0.3       # per malam, short
    slippage_pips: float = 0.0          # opsional, dibebankan saat fill

    def spread_price(self, spec: SymbolSpec) -> float:
        return self.spread_pips * spec.pip_size

    def slippage_price(self, spec: SymbolSpec) -> float:
        return self.slippage_pips * spec.pip_size

    def commission_cost(self, lots: float) -> float:
        """Komisi satu sisi (entry atau exit)."""
        return self.commission_per_lot * lots

    def swap_cost(self, direction: int, lots: float, nights: int,
                  wednesday_triples: int, spec: SymbolSpec) -> float:
        """Total swap (mata uang akun) untuk posisi yang ditahan `nights` malam.

        wednesday_triples = berapa dari malam itu jatuh di Rabu (dihitung 3x).
        direction: +1 long, -1 short.
        """
        per_night_pips = self.swap_long_pips if direction > 0 else self.swap_short_pips
        # Rabu dihitung 3x: tambah 2x ekstra untuk tiap malam Rabu.
        effective_nights = nights + 2 * wednesday_triples
        return per_night_pips * spec.pip_value_per_lot * lots * effective_nights
