import numpy as np
import pytest

from diel_engine.strategy.evaluator import Condition


def _ctx():
    return {
        "a": np.array([1.0, 2.0, 3.0, 2.0, 1.0]),
        "b": np.array([3.0, 2.5, 2.0, 2.5, 3.0]),
        "close": np.array([10.0, 11.0, 12.0, 11.5, 11.0]),
    }


def test_cross_over_detected():
    ctx = _ctx()
    c = Condition("cross_over(a, b)")
    # a melintas ke atas b di index 2 (a:2->3, b:2.5->2.0)
    assert c.eval(ctx, 2) is True
    assert c.eval(ctx, 1) is False


def test_cross_under_detected():
    ctx = _ctx()
    c = Condition("cross_under(a, b)")
    # a melintas ke bawah b di index 3 (a:3->2, b:2.0->2.5)
    assert c.eval(ctx, 3) is True


def test_comparison_and_boolean():
    ctx = _ctx()
    assert Condition("close > 11.5").eval(ctx, 2) is True
    assert Condition("close > 11.5").eval(ctx, 0) is False
    assert Condition("a > 1 and b < 3").eval(ctx, 1) is True


def test_nan_is_false():
    ctx = {"a": np.array([np.nan, 1.0]), "b": np.array([np.nan, 0.0])}
    assert Condition("a > b").eval(ctx, 0) is False
    assert Condition("cross_over(a, b)").eval(ctx, 1) is False  # i-1 NaN


def test_rejects_unsafe_expression():
    with pytest.raises(ValueError):
        Condition("__import__('os').system('echo hi')")
    with pytest.raises(ValueError):
        Condition("unknown_func(a)")


def test_rejects_unknown_reference():
    with pytest.raises(KeyError):
        Condition("does_not_exist > 1").eval(_ctx(), 1)
