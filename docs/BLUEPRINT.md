# Platform-DIEL — Blueprint

> Marketplace & sosial untuk strategi trading **terverifikasi**.
> Trader bikin ide → kita backtest pakai data & engine sendiri → kalau lolos verifikasi,
> mereka bisa pamer (flex) di leaderboard dan jual sebagai EA MT4/MT5.
>
> Fokus market awal: **Forex (MT4/MT5)**.
> Status dokumen: draft v0.1 — acuan desain sebelum coding.

---

## 1. Inti masalah & kenapa ini bisa hidup

Banyak orang jualan EA / sinyal forex dengan klaim "profit ribuan persen", tapi
**buktinya gampang dipalsukan** (screenshot, backtest yang di-overfit, akun cent yang
di-zoom). Kepercayaan di pasar ini rendah.

**Value proposition Platform-DIEL = pihak ketiga netral yang menjalankan dan
memverifikasi backtest sendiri.** User tidak meng-upload "hasil"; user meng-upload
**logika strateginya**, lalu *kami* yang menjalankan di data & engine kami. Badge
"Verified by DIEL" inilah produknya — bukan sekadar marketplace.

> ⚠️ Prinsip yang dipegang sepanjang dokumen ini: **backtest in-sample saja = bukti
> lemah.** Strategi gampang di-overfit. Kredibilitas dibangun berlapis (lihat §6).

---

## 2. Persona

| Persona | Kebutuhan |
|---|---|
| **Strategy Author** (trader/kuant) | Submit ide, dapat backtest jujur, badge, dan bisa monetisasi |
| **Buyer / Follower** | Cari EA yang *benar-benar* teruji, lihat track record asli, beli/sewa dengan aman |
| **Spectator** | Nonton leaderboard, equity curve, belajar — funnel jadi author/buyer |
| **Admin / Reviewer** | Jaga integritas, moderasi, tangani sengketa & anti-cheat |

---

## 3. Alur utama (happy path Author)

```
Daftar ─▶ Bikin strategi (builder/DSL)
       ─▶ Submit job backtest
       ─▶ Engine jalan: in-sample ─▶ out-of-sample ─▶ walk-forward
       ─▶ Skor & badge dihitung
       ─▶ (opsional) Forward test demo MT5 selama N minggu
       ─▶ Publish ke profil + leaderboard (flex)
       ─▶ (opsional) Generate EA MQL4/MQL5 + listing di marketplace
       ─▶ Buyer beli → terima EA berlisensi → revenue share
```

---

## 4. Arsitektur sistem

```
┌──────────────┐      ┌─────────────────┐      ┌──────────────────────┐
│  Web (Next)  │──────│  API (FastAPI)  │──────│  Postgres + Timescale │
│  profil,     │ REST │  auth, listing, │      │  user, strategy,      │
│  leaderboard,│ /WS  │  job, payment   │      │  run, result, market  │
│  builder     │      └────────┬────────┘      └──────────────────────┘
└──────────────┘               │
                               │ enqueue job
                        ┌──────▼───────┐      ┌────────────────────┐
                        │ Redis queue  │──────│  Backtest Workers   │
                        └──────────────┘      │  (Python, isolated) │
                                              │  engine + datafeed  │
                                              └─────────┬──────────┘
                                                        │
        ┌───────────────────────┬───────────────────────┤
        ▼                       ▼                       ▼
┌───────────────┐     ┌──────────────────┐    ┌──────────────────┐
│ Market data    │     │ Codegen service  │    │ MT5 forward-test  │
│ store (tick/M1)│     │ MQL4/MQL5/Pine   │    │ runner (demo acct)│
└───────────────┘     └──────────────────┘    └──────────────────┘
```

Komponen kunci:
- **Web (Next.js)** — UI publik: profil, leaderboard, equity curve interaktif, builder strategi, marketplace.
- **API (FastAPI/Python)** — auth, CRUD strategi, antrian job, pembayaran, lisensi.
- **Backtest Workers** — proses terisolasi (sandbox) yang menjalankan strategi user. **Wajib sandbox** karena menjalankan kode/logika dari user.
- **Market data store** — data forex historis (tick/M1) + metadata broker (spread, swap, sesi).
- **Codegen** — render strategi → MQL4 (MT4), MQL5 (MT5), dan Pine Script (sebagai output, lihat §8).
- **MT5 forward runner** — pakai paket Python `MetaTrader5` di akun demo untuk forward test nyata (diferensiasi besar untuk forex).

---

## 5. Tech stack (rekomendasi terpilih)

| Lapisan | Pilihan | Alasan |
|---|---|---|
| Web | **Next.js + TypeScript + Tailwind** | SSR untuk SEO leaderboard publik, ekosistem chart kuat (TradingView Lightweight Charts) |
| API | **FastAPI (Python)** | Satu bahasa dengan engine, async, typed |
| Engine | **Python** (numpy/pandas; opsi `vectorbt`/`backtrader`) | Ekosistem kuant terkaya; MT5 punya API Python resmi |
| DB | **Postgres + TimescaleDB** | Relasional + hypertable untuk time-series harga |
| Queue | **Redis + RQ/Celery** | Job backtest async, retry, prioritas |
| Storage | **S3-compatible** | Simpan file EA, artefak hasil, laporan |
| Sandbox | **Docker / gVisor / firecracker** | Isolasi eksekusi strategi user |
| Auth | **Auth.js / Clerk / Supabase Auth** | Cepat, aman |
| Payment | **Stripe (+ alternatif lokal: Xendit/Midtrans)** | Stripe rewel utk trading → siapkan alternatif lokal ID |

> Catatan forex: paket **`MetaTrader5` (Python)** bisa tarik data historis & jalankan
> demo forward test — ini jembatan langsung ke ekosistem MT5.

---

## 6. Mekanisme verifikasi — JANTUNG produk

Badge tidak diberikan dari satu backtest. Ada **gerbang berlapis**:

1. **In-sample backtest** — periode data untuk mengembangkan strategi. Hasil ditampilkan tapi **tidak** menentukan badge.
2. **Out-of-sample (OOS)** — periode data yang strateginya *tidak pernah lihat*. Performa di sini yang dihitung.
3. **Walk-forward analysis** — geser jendela in-sample/OOS berulang; menguji apakah strategi tetap robust lintas waktu, bukan cuma beruntung di satu periode.
4. **Robustness checks** — uji sensitivitas parameter (apakah profit cuma di 1 set parameter ajaib = tanda overfit), Monte Carlo pada urutan trade, multi-pair / multi-timeframe.
5. **Forward test (opsional, badge tertinggi)** — jalan di akun **demo MT5** real-time selama N minggu. Ini yang paling sulit dipalsukan.

### Metrik yang dilaporkan
CAGR, max drawdown, Sharpe, Sortino, profit factor, win rate, expectancy, jumlah trade,
**deflated Sharpe / overfit probability (PBO)**, exposure, recovery factor.

### Tingkat badge (contoh)
| Badge | Syarat |
|---|---|
| 🟦 Backtested | Lolos in-sample + OOS dasar |
| 🟩 Robust | Lolos walk-forward + robustness checks |
| 🟨 Forward-Verified | + forward demo ≥ N minggu dengan hasil konsisten |
| 🟧 Live-Tracked | + track record akun live terhubung (Investor password / read-only) |

**Anti-cheat:** lihat §11.

---

## 7. Skema data (ringkas)

```
users(id, handle, email, role, payout_account, created_at)
strategies(id, author_id, name, spec_json, market, symbol, timeframe, visibility, created_at)
strategy_versions(id, strategy_id, version, spec_hash, spec_json)
backtest_runs(id, strategy_version_id, phase, period_start, period_end,
              dataset_id, params_json, status, started_at, finished_at)
run_results(run_id, metrics_json, equity_curve_ref, trades_ref, badge_contrib)
verifications(strategy_id, badge_level, score, computed_at, breakdown_json)
datasets(id, symbol, source, granularity, period_start, period_end, checksum)  -- data versioned
listings(id, strategy_id, price, license_type, status)            -- marketplace
orders(id, buyer_id, listing_id, amount, status, created_at)
licenses(id, order_id, ea_artifact_ref, account_binding, expires_at)  -- DRM/binding
forward_tests(id, strategy_id, mt5_demo_ref, start, status, live_metrics_json)
```

Prinsip penting: **dataset di-version + checksum.** Hasil verifikasi harus
*reproducible* — kalau data berubah, run lama tetap bisa diaudit.

---

## 8. Format strategi & codegen

### Format strategi (DSL netral)
Daripada terima kode bebas (bahaya & susah diverifikasi), strategi dideskripsikan
sebagai **spec terstruktur** (JSON/DSL) yang **market-agnostic**:

```jsonc
{
  "symbol": "EURUSD", "timeframe": "H1",
  "indicators": [
    {"id": "ema_fast", "type": "EMA", "period": 20},
    {"id": "ema_slow", "type": "EMA", "period": 50}
  ],
  "entry_long":  "cross_over(ema_fast, ema_slow)",
  "entry_short": "cross_under(ema_fast, ema_slow)",
  "stop_loss":   {"type": "atr", "mult": 2.0},
  "take_profit": {"type": "rr", "ratio": 1.5},
  "risk":        {"per_trade_pct": 1.0}
}
```

Keuntungan: bisa di-backtest engine kami **dan** di-generate ke target mana pun.
Untuk power user, sediakan jalur lanjut (Python tersandbox) di fase berikutnya.

### Codegen target
- **MQL5** (MT5 EA) — target utama.
- **MQL4** (MT4 EA) — pasar masih besar.
- **Pine Script** — *catatan penting:* Pine **tidak bisa dijalankan di luar TradingView**,
  jadi Pine adalah **output ekspor** (biar user pakai di TV), **bukan** yang kita backtest.
  Yang kita backtest = spec/DSL di engine sendiri.

---

## 9. Backtest engine — spesifik Forex

Forex butuh pemodelan biaya yang akurat, kalau tidak hasilnya bohong:
- **Spread** (variabel per sesi), **commission**, **swap/rollover** harian (triple swap Rabu).
- **Lot sizing, leverage, margin, margin call**.
- **Slippage** & eksekusi realistis; gap akhir pekan.
- **Sesi pasar** (Sydney/Tokyo/London/NY) & news spike.
- Eksekusi berbasis **tick atau M1** untuk presisi SL/TP intrabar.

### Sumber data forex
- **Dukascopy** — tick historis gratis (kualitas bagus). *(rekomendasi awal)*
- **HistData.com** — M1 gratis.
- Feed broker / MetaQuotes — untuk spread/swap realistis per broker.

> Disклaimer realistis: spread & swap **beda per broker**, jadi hasil di-label dengan
> asumsi biaya yang dipakai. Transparansi = kepercayaan.

---

## 10. Marketplace, monetisasi & lisensi

- **Model harga:** beli putus, sewa bulanan, atau revenue-share/PAMM (fase lanjut).
- **Lisensi/DRM EA:** EA MT4/MT5 di-bind ke **nomor akun** pembeli (teknik umum di MQL),
  + aktivasi online opsional. Mencegah resell liar.
- **Revenue share:** platform ambil komisi (mis. 20–30%).
- **Escrow / refund window:** lindungi pembeli; tahan dana sampai EA terverifikasi jalan.
- **Payment:** Stripe global + **Xendit/Midtrans** untuk Indonesia (kartu, VA, e-wallet).

---

## 11. Integritas & anti-cheat

Karena seluruh nilai = kepercayaan, ini bukan opsional:
- **Author tidak pilih sendiri periode OOS** — platform yang menetapkan & menyembunyikan.
- **Data terkunci & versioned** — author tak bisa nyuapin data masa depan (look-ahead bias).
- **Deteksi overfit** — penalti kalau performa kolaps saat parameter digeser sedikit (PBO).
- **Eksekusi tersandbox** — strategi user jalan terisolasi, tanpa akses jaringan/FS.
- **Hindari survivorship & look-ahead bias** di engine (no future leak).
- **Forward/live** memberi badge tertinggi justru karena paling sulit dimanipulasi.

---

## 12. Legal / compliance (jangan diremehkan)

- **Disclaimer wajib:** "Past performance is not indicative of future results", "bukan
  nasihat finansial". Tampil jelas di tiap halaman performa & listing.
- **Lisensi regional** — jualan sinyal/strategi bisa kena aturan (mis. BAPPEBTI/OJK di ID,
  ESMA di EU, NFA/CFTC di US). Perlu kajian hukum sebelum monetisasi.
- **KYC/AML** untuk payout uang.
- **ToS yang jelas** soal kepemilikan strategi, refund, dan tanggung jawab.

> Legal bukan blocker untuk MVP teknis, tapi **wajib beres sebelum aktifkan pembayaran.**

---

## 13. Roadmap berfase

### Fase 0 — Fondasi (engine + data) 🎯 *titik mulai berikutnya*
- Skema DB + ingest data forex (Dukascopy EURUSD M1/tick).
- Backtest engine inti: eksekusi spec DSL + biaya forex (spread/swap/commission).
- 1 strategi contoh (EMA cross) jalan end-to-end di CLI, hasil reproducible.
- **Deliverable:** "kasih spec → keluar metrik + equity curve yang bener."

### Fase 1 — Verifikasi
- Pipeline in-sample → OOS → walk-forward + perhitungan badge/score.
- Robustness & overfit checks (PBO, sweep parameter).

### Fase 2 — Web & sosial (flex)
- Profil author, leaderboard, equity curve interaktif, halaman strategi publik.
- Auth + submit job lewat UI.

### Fase 3 — Marketplace & codegen
- Codegen MQL5/MQL4/Pine, listing, pembayaran, lisensi/DRM, revenue share.

### Fase 4 — Forward & live
- Forward test demo MT5 otomatis; koneksi akun live read-only; badge tertinggi.

---

## 14. Risiko & pertanyaan terbuka

- **Kualitas data forex per broker** — perbedaan spread/swap bisa bikin debat hasil. → label asumsi transparan.
- **Pine tidak bisa dieksekusi server** — sudah diatasi: Pine = ekspor, bukan sumber backtest.
- **Compliance jualan strategi** — perlu kajian hukum per region sebelum monetisasi.
- **Biaya forward test** (jaga banyak akun demo MT5) — perlu infra runner.
- **DSL vs kode bebas** — DSL aman & verifiable tapi kurang fleksibel; jalur Python sandbox di fase lanjut.

---

## 15. Keputusan yang sudah diambil
- Market awal: **Forex (MT4/MT5)**.
- Stack: **Next.js + FastAPI/Python + Postgres/Timescale + Redis**.
- Mulai bangun dari **Fase 0 (engine + data)**, bukan UI.
- Strategi via **DSL terstruktur**, Pine sebagai output ekspor.

> Langkah konkret berikutnya: implementasi **Fase 0** — skema DB minimal, ingester
> data Dukascopy, dan engine backtest inti dengan satu strategi contoh.
