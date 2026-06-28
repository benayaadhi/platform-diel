"""Pemisahan data untuk verifikasi.

Prinsip anti-cheat (BLUEPRINT §11): author TIDAK memilih sendiri periode OOS.
Platform yang menetapkan pembagian; di sini fungsinya deterministik berbasis
posisi/urutan waktu sehingga tak bisa dimanipulasi.
"""
from __future__ import annotations

from typing import List, Tuple

from ..data.models import Bars


def _slice(bars: Bars, lo: int, hi: int) -> Bars:
    return Bars(bars.symbol, bars.timeframe, bars.df.iloc[lo:hi].copy())


def train_test_split(bars: Bars, oos_ratio: float = 0.3) -> Tuple[Bars, Bars]:
    """Split kronologis: bagian awal = in-sample, bagian akhir = out-of-sample.

    OOS selalu di AKHIR (data terbaru) — meniru kondisi nyata "train masa lalu,
    uji masa depan".
    """
    if not 0.0 < oos_ratio < 1.0:
        raise ValueError("oos_ratio harus di (0,1)")
    n = len(bars)
    cut = int(n * (1.0 - oos_ratio))
    if cut < 1 or cut >= n:
        raise ValueError("Data terlalu sedikit untuk split")
    return _slice(bars, 0, cut), _slice(bars, cut, n)


def walk_forward_folds(
    bars: Bars,
    n_folds: int = 4,
    *,
    anchored: bool = True,
) -> List[Tuple[Bars, Bars]]:
    """Hasilkan pasangan (in_sample, out_of_sample) untuk walk-forward.

    Data dibagi n_folds+1 blok sama besar.
    - anchored=True : IS = blok[0..k-1] (tumbuh dari awal), OOS = blok[k].
    - anchored=False: IS = blok[k-1] (jendela bergulir tetap), OOS = blok[k].
    """
    if n_folds < 1:
        raise ValueError("n_folds harus >= 1")
    n = len(bars)
    block = n // (n_folds + 1)
    if block < 2:
        raise ValueError("Data terlalu sedikit untuk jumlah fold ini")
    folds: List[Tuple[Bars, Bars]] = []
    for k in range(1, n_folds + 1):
        oos_lo, oos_hi = k * block, (k + 1) * block if k < n_folds else n
        is_lo = 0 if anchored else (k - 1) * block
        folds.append((_slice(bars, is_lo, k * block), _slice(bars, oos_lo, oos_hi)))
    return folds


def time_slices(bars: Bars, n_slices: int = 8) -> List[Bars]:
    """Pecah data jadi n_slices blok kontigu (untuk matriks performa CSCV/PBO)."""
    if n_slices < 2:
        raise ValueError("n_slices harus >= 2")
    n = len(bars)
    size = n // n_slices
    if size < 2:
        raise ValueError("Data terlalu sedikit untuk jumlah slice ini")
    out = []
    for s in range(n_slices):
        lo = s * size
        hi = (s + 1) * size if s < n_slices - 1 else n
        out.append(_slice(bars, lo, hi))
    return out
