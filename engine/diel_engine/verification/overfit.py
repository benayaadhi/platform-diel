"""Deteksi overfit.

1) PBO (Probability of Backtest Overfitting) via CSCV — metode Bailey, Borwein,
   Lopez de Prado & Zhu (2014). Idenya: bila konfigurasi terbaik di in-sample
   cenderung TIDAK terbaik di out-of-sample lintas banyak pembelahan waktu, maka
   "kemenangan" backtest kemungkinan besar hasil overfit/keberuntungan.

2) robust_fraction — proporsi konfigurasi grid yang tetap profit di data unseen.
   Region luas yang profit = robust; cuma satu titik ajaib yang profit = rapuh.
"""
from __future__ import annotations

import math
from itertools import combinations
from typing import Dict, List, Tuple

import numpy as np


def pbo_cscv(perf_matrix: np.ndarray) -> Tuple[float, Dict[str, float]]:
    """Hitung PBO dari matriks performa (n_slices x n_configs).

    Tiap sel = skor objektif konfigurasi pada satu slice waktu.
    Return (pbo, detail). pbo di [0,1]; makin tinggi makin overfit.
    """
    M = np.asarray(perf_matrix, dtype=float)
    S, N = M.shape
    if N < 2:
        return float("nan"), {"reason": "butuh >= 2 konfigurasi", "n_configs": N}
    if S < 4 or S % 2 != 0:
        return float("nan"), {"reason": "butuh n_slices genap >= 4", "n_slices": S}

    half = S // 2
    all_idx = set(range(S))
    lambdas: List[float] = []
    seen = set()
    for is_idx in combinations(range(S), half):
        oos_idx = tuple(sorted(all_idx - set(is_idx)))
        # Hindari pasangan simetris ganda (IS,OOS) vs (OOS,IS).
        key = frozenset((is_idx, oos_idx))
        if key in seen:
            continue
        seen.add(key)

        is_perf = M[list(is_idx)].mean(axis=0)
        oos_perf = M[list(oos_idx)].mean(axis=0)
        n_star = int(np.argmax(is_perf))           # terbaik di IS
        # peringkat n_star di OOS (1=terburuk .. N=terbaik)
        order = np.argsort(oos_perf, kind="stable")
        rank = int(np.where(order == n_star)[0][0]) + 1
        omega = rank / (N + 1)
        omega = min(max(omega, 1e-6), 1 - 1e-6)
        lambdas.append(math.log(omega / (1 - omega)))

    arr = np.array(lambdas)
    pbo = float(np.mean(arr <= 0.0))  # prob best-IS jatuh di bawah median OOS
    return pbo, {
        "n_splits": len(lambdas),
        "n_configs": N,
        "n_slices": S,
        "mean_logit": float(arr.mean()) if len(arr) else float("nan"),
    }


def robust_fraction(oos_scores: List[float]) -> float:
    """Fraksi konfigurasi yang skor objektifnya > 0 pada data OOS."""
    if not oos_scores:
        return 0.0
    arr = np.array(oos_scores, dtype=float)
    return float(np.mean(arr > 0.0))
