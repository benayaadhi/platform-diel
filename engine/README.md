# diel-engine — Backtest & Verification Engine (Fase 0–1)

Jantung "pembuktian" Platform-DIEL: terima **spec strategi (DSL)** + data forex,
keluarkan **metrik + equity curve** yang **deterministik & reproducible** (Fase 0),
lalu jalankan **verifikasi berlapis** (IS/OOS, walk-forward, deteksi overfit) yang
menghasilkan **skor + badge** (Fase 1).

Lihat `../docs/BLUEPRINT.md` untuk gambaran besar produk.

## Kenapa engine sendiri?
Karena value platform = **kita yang menjalankan backtest**, bukan percaya screenshot
user. User submit *logika* (spec), engine kita yang eksekusi di data & asumsi biaya kita.

## Instalasi
```bash
cd engine
pip install -e ".[dev]"      # atau: pip install numpy pandas pytest
```

## Pakai (CLI)
```bash
# Data sintetis (offline, deterministik) — bukti engine jalan tanpa jaringan
python -m diel_engine.cli backtest --strategy examples/ema_cross.json \
    --data synthetic --bars 5000 --seed 7

# Data CSV (kolom: timestamp,open,high,low,close,volume)
python -m diel_engine.cli backtest --strategy examples/ema_cross.json \
    --data csv --csv EURUSD_H1.csv --json-out result.json --equity-out equity.csv

# Data nyata Dukascopy (butuh jaringan)
python -m diel_engine.cli backtest --strategy examples/ema_cross.json \
    --data dukascopy --start 2023-01-01 --end 2023-02-01
```

## Pakai (Python)
```python
from diel_engine.data.loaders import synthetic_bars
from diel_engine.strategy.spec import load_spec
from diel_engine.backtest.engine import run_backtest

bars = synthetic_bars("EURUSD", "H1", n=5000, seed=7)
spec = load_spec("examples/ema_cross.json")
result = run_backtest(bars, spec, initial_balance=10_000)
print(result.summary())
```

## Verifikasi berlapis (Fase 1) — kenapa badge ini berarti

```bash
python -m diel_engine.cli verify --strategy examples/ema_cross.json \
    --data synthetic --bars 6000 --seed 7 --folds 4 --slices 8
```

Pipeline (lihat `diel_engine/verification/`):
1. **Split IS/OOS** kronologis — OOS = data terbaru, **ditetapkan platform** (anti-cheat: author tak pilih sendiri).
2. **Optimisasi grid di IS** (`param_grid` di spec) → pilih konfigurasi terbaik.
3. **Uji di OOS** (data belum pernah dilihat).
4. **Robust fraction** — berapa % konfigurasi tetap profit di OOS (region luas = robust, satu titik ajaib = rapuh).
5. **PBO (CSCV)** — Probability of Backtest Overfitting (Bailey et al. 2014): seberapa sering "juara IS" gagal di OOS lintas pembelahan waktu.
6. **Walk-forward** — consistency (% fold OOS+) & efficiency (luruhnya performa OOS vs IS).
7. **Skor 0..100 + badge**: `Unverified` → `Backtested` (🟦) → `Robust` (🟩).

> Badge `Forward-Verified`/`Live-Tracked` butuh forward test demo MT5 (Fase 4),
> jadi verifikasi backtest ini maksimal memberi **Robust**.

Contoh hasil pada data sintetis: satu window OOS bisa kelihatan profit, tapi PBO
tinggi + walk-forward efficiency rendah menahan badge `Robust` — persis perilaku
yang diinginkan (menangkap overfit yang lolos dari backtest tunggal).

## Format strategi (DSL)
Strategi = **data**, bukan kode bebas (aman + verifiable + bisa di-codegen nanti).
Lihat `examples/ema_cross.json`. Ekspresi sinyal mendukung:
`cross_over`, `cross_under`, `rising`, `falling`, operator `> < >= <= == !=`,
`and/or/not`, aritmetika, dan referensi indikator / harga (`close/open/high/low`).
Indikator: `EMA`, `SMA`, `ATR`, `RSI`.

## Prinsip korektnes
- **Next-bar execution**: sinyal di close bar i → order isi di open bar i+1 (anti look-ahead).
- **SL/TP intrabar** pakai high/low; bila SL & TP kena di bar sama → SL didahulukan (konservatif).
- **Biaya forex eksplisit**: spread, commission/lot/sisi, swap per malam (Rabu 3x).
  Asumsi biaya ikut disimpan di hasil agar transparan/auditable.
- **Position sizing berbasis risiko**: % equity per trade dari jarak stop.
- **Evaluator ekspresi tersandbox** (whitelist AST) — spec user tak bisa eksekusi kode arbitrer.

## Struktur
```
diel_engine/
  data/      models (symbol/bars), loaders (csv/synthetic), dukascopy (ingester)
  strategy/  spec (DSL), indicators, evaluator (sinyal aman)
  backtest/  costs (biaya forex), engine (event-loop), metrics, results
  verification/  splits, params, optimize, overfit (PBO), walkforward, verify, report
  cli.py     (subcommand: backtest, verify)
examples/ema_cross.json
tests/
```

## Test
```bash
python -m pytest -q     # 29 test: indikator, evaluator, engine e2e, biaya, anti-lookahead, verifikasi
```

## Keterbatasan Fase 0 (sengaja — masuk fase berikutnya)
- **Metrik in-sample saja TIDAK cukup untuk badge.** Verifikasi berlapis
  (out-of-sample, walk-forward, deteksi overfit/PBO) = **Fase 1**.
- **Sharpe/Sortino** dihitung per-bar termasuk bar tanpa posisi → magnitudo bisa
  terdistorsi saat annualisasi timeframe kecil. Akan disempurnakan (resample/risk-based) di Fase 1.
- **Swap** memakai aproksimasi rollover midnight UTC (Rabu 3x). Model presisi per-broker menyusul.
- **pip value** diasumsikan konstan (cocok untuk pair quote-USD dengan akun USD).
  Konversi kurs lintas-pair menyusul.
- Satu posisi pada satu waktu, no pyramiding/hedging.

> Catatan validasi: strategi contoh **rugi pada data sintetis random-walk**. Itu
> benar — trend-following tanpa edge + biaya memang seharusnya rugi. Engine yang
> "selalu profit" pada random walk = tanda bug look-ahead.
