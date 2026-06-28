import numpy as np

from diel_engine.strategy import indicators as ind


def test_sma_basic():
    x = np.array([1, 2, 3, 4, 5], dtype=float)
    out = ind.sma(x, 3)
    assert np.isnan(out[0]) and np.isnan(out[1])
    np.testing.assert_allclose(out[2:], [2.0, 3.0, 4.0])


def test_ema_warmup_and_trend():
    x = np.arange(1, 21, dtype=float)
    out = ind.ema(x, 5)
    # Periode warmup NaN, lalu seed = SMA 5 pertama = 3.0
    assert np.all(np.isnan(out[:4]))
    assert abs(out[4] - 3.0) < 1e-9
    # EMA harus naik mengikuti seri yang naik & < nilai terakhir
    assert out[-1] < x[-1]
    assert out[-1] > out[-2]


def test_atr_positive():
    n = 50
    high = np.linspace(10, 12, n)
    low = high - 0.5
    close = (high + low) / 2
    out = ind.atr(high, low, close, 14)
    assert np.all(np.isnan(out[:13]))
    assert np.all(out[14:] > 0)


def test_rsi_bounds():
    rng = np.random.default_rng(0)
    x = np.cumsum(rng.normal(0, 1, 200)) + 100
    out = ind.rsi(x, 14)
    valid = out[~np.isnan(out)]
    assert np.all((valid >= 0) & (valid <= 100))
