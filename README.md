# Platform-DIEL

> Marketplace & sosial untuk **strategi trading forex yang benar-benar terverifikasi**.
> Trader bikin ide → kita backtest pakai engine & data sendiri → kalau lolos
> verifikasi berlapis (out-of-sample, walk-forward, anti-overfit), mereka dapat
> **badge**, pamer di leaderboard, dan (nanti) jual sebagai EA MT4/MT5.

Diferensiasi: **platform yang menjalankan backtest**, bukan percaya screenshot user.
Badge dibangun dari gerbang yang sulit dipalsukan. Lihat [`docs/BLUEPRINT.md`](docs/BLUEPRINT.md).

## Struktur monorepo

| Folder | Isi | Status |
|---|---|---|
| [`engine/`](engine/) | Engine backtest forex + verifikasi (Python) | ✅ Fase 0–1 |
| [`backend/`](backend/) | API FastAPI (auth, strategi, run, leaderboard) | ✅ Fase 2 |
| [`web/`](web/) | Frontend Next.js (leaderboard, detail, equity chart) | ✅ Fase 2 |
| [`docs/`](docs/) | Blueprint produk & arsitektur | — |

## Quickstart lokal (2 terminal)

**Prasyarat:** Python 3.10+, Node 18+.

### 1) Engine + Backend
```bash
cd backend
pip install -e ../engine          # engine backtest/verify
pip install -r requirements.txt
python -m scripts.seed            # (opsional) isi data demo
uvicorn app.main:app --reload --port 8000
# API: http://localhost:8000/docs
```

### 2) Frontend
```bash
cd web
npm install
npm run dev
# Buka http://localhost:3000
```

> Penting: buka via **http://localhost:3000** (bukan 127.0.0.1) agar cocok dengan
> CORS default backend.

### 3) Coba alur
1. Daftar akun → buat strategi (spec contoh sudah terisi).
2. Klik **Jalankan Backtest** → lihat equity curve + metrik.
3. Klik **Verifikasi** → dapat skor + badge (in-sample/OOS/walk-forward/PBO).
4. Lihat **Leaderboard** terurut skor.

User demo dari seed: `demo@diel.app` / `demo12345`.

## Test
```bash
cd engine  && python -m pytest -q     # 29 test (engine + verifikasi)
cd backend && python -m pytest -q     # 7 test (alur API)
cd web     && npm run build           # type-check + build
```

## Deploy (target produksi)
- **Frontend (Next.js)** → Vercel. Set `NEXT_PUBLIC_API_URL` ke URL backend.
- **Backend + engine** → Railway / Render / Fly.io (bukan Vercel/Netlify — engine butuh proses panjang).
- **Database + Auth + Storage** → Supabase. Set `DATABASE_URL` ke Postgres Supabase.

## Roadmap
- ✅ Fase 0 — Engine backtest + data
- ✅ Fase 1 — Verifikasi berlapis (badge)
- ✅ Fase 2 — Web & sosial (leaderboard, profil, equity curve)
- ⬜ Fase 3 — Marketplace & codegen (MQL5/MQL4/Pine, listing, payment, lisensi)
- ⬜ Fase 4 — Forward & live (demo MT5, badge tertinggi)

---
*Past performance is not indicative of future results. Bukan nasihat finansial.*
