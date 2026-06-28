"""Evaluator ekspresi sinyal yang AMAN & terbatas.

Ekspresi seperti  "cross_over(ema_fast, ema_slow)"  diparse dengan `ast` lalu
dievaluasi terhadap series indikator/harga yang sudah dihitung, pada index bar i.

Yang diizinkan: Name (indikator/harga), angka konstan, operator aritmetika &
perbandingan, boolean and/or/not, dan fungsi whitelist (cross_over, cross_under,
rising, falling). Selain itu -> ditolak. Ini mencegah eksekusi kode sembarangan
dari spec user.

Tanpa look-ahead: evaluasi pada index i hanya menyentuh data index i dan i-1.
"""
from __future__ import annotations

import ast
import math
from typing import Dict, Union

import numpy as np

Number = Union[int, float]


def _at(v, i: int) -> float:
    """Ambil nilai skalar pada index i dari array, atau kembalikan skalar apa adanya."""
    if isinstance(v, np.ndarray):
        return float(v[i])
    return float(v)


def _cross_over(a, b, i: int) -> bool:
    if i < 1:
        return False
    p = _at(a, i - 1) - _at(b, i - 1)
    c = _at(a, i) - _at(b, i)
    if math.isnan(p) or math.isnan(c):
        return False
    return p <= 0.0 and c > 0.0


def _cross_under(a, b, i: int) -> bool:
    if i < 1:
        return False
    p = _at(a, i - 1) - _at(b, i - 1)
    c = _at(a, i) - _at(b, i)
    if math.isnan(p) or math.isnan(c):
        return False
    return p >= 0.0 and c < 0.0


def _rising(a, i: int) -> bool:
    if i < 1:
        return False
    p, c = _at(a, i - 1), _at(a, i)
    return not (math.isnan(p) or math.isnan(c)) and c > p


def _falling(a, i: int) -> bool:
    if i < 1:
        return False
    p, c = _at(a, i - 1), _at(a, i)
    return not (math.isnan(p) or math.isnan(c)) and c < p


# Fungsi whitelist; semuanya butuh index i (disuntik saat evaluasi).
_FUNCS = {
    "cross_over": _cross_over,
    "cross_under": _cross_under,
    "rising": _rising,
    "falling": _falling,
}

_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}

_CMPOPS = {
    ast.Gt: lambda a, b: a > b,
    ast.Lt: lambda a, b: a < b,
    ast.GtE: lambda a, b: a >= b,
    ast.LtE: lambda a, b: a <= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}


class Condition:
    """Ekspresi sinyal terkompilasi, bisa dievaluasi berkali-kali per index."""

    def __init__(self, expr: str):
        self.source = expr
        self._node = ast.parse(expr, mode="eval").body
        self._validate(self._node)

    @staticmethod
    def _validate(node: ast.AST) -> None:
        allowed = (
            ast.BoolOp, ast.UnaryOp, ast.Not, ast.And, ast.Or,
            ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div,
            ast.Compare, ast.Gt, ast.Lt, ast.GtE, ast.LtE, ast.Eq, ast.NotEq,
            ast.Call, ast.Name, ast.Load, ast.Constant,
        )
        for n in ast.walk(node):
            if not isinstance(n, allowed):
                raise ValueError(f"Konstruksi tidak diizinkan dalam ekspresi: {type(n).__name__}")
            if isinstance(n, ast.Call):
                if not isinstance(n.func, ast.Name) or n.func.id not in _FUNCS:
                    raise ValueError(f"Fungsi tidak dikenal: {ast.dump(n.func)}")
                if n.keywords:
                    raise ValueError("Argumen keyword tidak didukung")
            if isinstance(n, ast.Constant) and not isinstance(n.value, (int, float)):
                raise ValueError("Hanya konstanta numerik yang diizinkan")

    def eval(self, ctx: Dict[str, np.ndarray], i: int) -> bool:
        return bool(self._eval(self._node, ctx, i))

    def _eval(self, node: ast.AST, ctx: Dict[str, np.ndarray], i: int):
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in ctx:
                raise KeyError(f"Referensi tak dikenal '{node.id}' dalam ekspresi")
            return ctx[node.id]  # array (di-resolve ke skalar saat dibutuhkan)
        if isinstance(node, ast.Call):
            fn = _FUNCS[node.func.id]  # type: ignore[attr-defined]
            args = [self._eval(a, ctx, i) for a in node.args]
            return fn(*args, i)
        if isinstance(node, ast.BoolOp):
            vals = [self._eval(v, ctx, i) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(bool(v) for v in vals)
            return any(bool(v) for v in vals)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(self._eval(node.operand, ctx, i))
        if isinstance(node, ast.BinOp):
            a = _at(self._eval(node.left, ctx, i), i)
            b = _at(self._eval(node.right, ctx, i), i)
            return _BINOPS[type(node.op)](a, b)
        if isinstance(node, ast.Compare):
            left = _at(self._eval(node.left, ctx, i), i)
            result = True
            for op, comp in zip(node.ops, node.comparators):
                right = _at(self._eval(comp, ctx, i), i)
                if math.isnan(left) or math.isnan(right):
                    return False
                result = result and _CMPOPS[type(op)](left, right)
                left = right
            return result
        raise ValueError(f"Node tak tertangani: {type(node).__name__}")
