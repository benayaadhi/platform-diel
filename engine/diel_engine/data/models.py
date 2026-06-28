"""Model data inti: spesifikasi symbol forex + container OHLC bars.

Catatan forex penting yang sering bikin backtest bohong:
- pip != point. Untuk EURUSD 5-digit, point=0.00001 tapi 1 pip=0.0001.
- pip value per lot dipakai untuk position sizing & P&L.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SymbolSpec:
    """Metadata satu instrumen forex.

    pip_value_per_lot diasumsikan dalam mata uang akun. Untuk pair quote-USD
    (mis. EURUSD) dengan akun USD: pip_size * contract_size = 0.0001 * 100000 = $10.
    Untuk pair lain (mis. USDJPY) nilainya berbeda & bergantung kurs — di Fase 0
    kita pakai nilai konstan yang transparan; konversi kurs masuk fase berikutnya.
    """

    name: str
    digits: int            # jumlah desimal harga (EURUSD = 5)
    point: float           # ukuran 1 point = 10**-digits
    pip_size: float        # ukuran 1 pip (biasanya 10 * point untuk 5/3-digit)
    contract_size: float   # unit per 1.0 lot (standar forex = 100_000)

    @property
    def pip_value_per_lot(self) -> float:
        # Nilai (mata uang quote) dari pergerakan 1 pip untuk 1.0 lot.
        return self.pip_size * self.contract_size


# Registry kecil; diperluas saat menambah pair. Sumber kebenaran tunggal.
SYMBOLS: Dict[str, SymbolSpec] = {
    "EURUSD": SymbolSpec("EURUSD", digits=5, point=1e-5, pip_size=1e-4, contract_size=100_000),
    "GBPUSD": SymbolSpec("GBPUSD", digits=5, point=1e-5, pip_size=1e-4, contract_size=100_000),
    "USDJPY": SymbolSpec("USDJPY", digits=3, point=1e-3, pip_size=1e-2, contract_size=100_000),
}


def get_symbol(name: str) -> SymbolSpec:
    key = name.upper()
    if key not in SYMBOLS:
        raise KeyError(f"Symbol '{name}' belum terdaftar di SYMBOLS registry")
    return SYMBOLS[key]


@dataclass
class Bars:
    """Container OHLC ber-timestamp untuk satu symbol+timeframe.

    Disimpan sebagai DataFrame index DatetimeIndex (UTC, urut naik) dengan kolom
    open/high/low/close/volume. Wrapper ini menjaga invarian & kasih akses numpy
    cepat ke engine.
    """

    symbol: str
    timeframe: str
    df: pd.DataFrame

    REQUIRED = ("open", "high", "low", "close", "volume")

    def __post_init__(self) -> None:
        missing = [c for c in self.REQUIRED if c not in self.df.columns]
        if missing:
            raise ValueError(f"Bars kekurangan kolom: {missing}")
        if not isinstance(self.df.index, pd.DatetimeIndex):
            raise ValueError("Bars.df harus pakai DatetimeIndex")
        if not self.df.index.is_monotonic_increasing:
            self.df = self.df.sort_index()
        # Buang baris duplikat timestamp (jaga yang terakhir).
        self.df = self.df[~self.df.index.duplicated(keep="last")]

    def __len__(self) -> int:
        return len(self.df)

    def series(self, name: str) -> np.ndarray:
        """Ambil kolom harga sebagai array float (close/open/high/low/volume)."""
        if name not in self.df.columns:
            raise KeyError(f"Kolom '{name}' tidak ada di bars")
        return self.df[name].to_numpy(dtype=float)

    @property
    def index(self) -> pd.DatetimeIndex:
        return self.df.index  # type: ignore[return-value]
