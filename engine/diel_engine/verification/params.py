"""Ruang parameter & override spec untuk optimisasi.

Strategi base dideskripsikan sekali (dict JSON). Parameter yang bisa dioptimisasi
dideklarasikan sebagai `param_grid` (di spec atau diberikan eksternal), mis.:

    {
      "indicators.ema_fast.period": [10, 15, 20],
      "indicators.ema_slow.period": [40, 50, 60],
      "stop_loss.mult": [1.5, 2.0, 2.5]
    }

Override path:
- "indicators.<id>.<field>" -> cari indikator ber-id <id>, set field-nya.
- selain itu -> jalur bertitik ke dict bersarang (mis. "stop_loss.mult").

Memisahkan param-space dari core spec menjaga DSL tetap bersih & aman.
"""
from __future__ import annotations

import copy
import itertools
from typing import Any, Dict, List, Tuple


def apply_overrides(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Kembalikan salinan dalam `base` dengan override diterapkan (base tak diubah)."""
    spec = copy.deepcopy(base)
    for path, value in overrides.items():
        parts = path.split(".")
        if parts[0] == "indicators":
            if len(parts) != 3:
                raise ValueError(f"Path indikator tidak valid: {path}")
            _, ind_id, field = parts
            found = False
            for ind in spec.get("indicators", []):
                if ind.get("id") == ind_id:
                    ind[field] = value
                    found = True
                    break
            if not found:
                raise KeyError(f"Indikator '{ind_id}' tidak ditemukan untuk override {path}")
        else:
            node = spec
            for p in parts[:-1]:
                if p not in node or not isinstance(node[p], dict):
                    node[p] = {}
                node = node[p]
            node[parts[-1]] = value
    return spec


def expand_grid(grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Cartesian product dari param_grid -> daftar dict override konkret."""
    if not grid:
        return [{}]
    keys = list(grid.keys())
    combos = itertools.product(*(grid[k] for k in keys))
    return [dict(zip(keys, vals)) for vals in combos]


def get_grid(spec_dict: Dict[str, Any]) -> Dict[str, List[Any]]:
    """Ambil param_grid dari spec (meta.param_grid atau param_grid top-level)."""
    if "param_grid" in spec_dict:
        return spec_dict["param_grid"]
    return spec_dict.get("meta", {}).get("param_grid", {})


def overrides_key(overrides: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    """Kunci hashable & stabil untuk satu konfigurasi (untuk cache/identitas)."""
    return tuple(sorted(overrides.items()))
