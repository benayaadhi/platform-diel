# diel-api — Backend (Fase 2)

API FastAPI yang menyambungkan **engine backtest/verify** ke web: auth, strategi,
menjalankan backtest & verifikasi, leaderboard, equity curve.

- **Lokal**: SQLite (zero-setup), engine jalan sebagai background task.
- **Produksi**: ganti `DATABASE_URL` ke Postgres **Supabase**; pindahkan eksekusi
  ke worker Redis (Fase 3). Frontend Next.js → **Vercel**.

## Setup
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # opsional
pip install -e ../engine            # engine backtest/verify
pip install -r requirements.txt
cp .env.example .env                # sesuaikan bila perlu
```

## Jalankan
```bash
uvicorn app.main:app --reload --port 8000
# Dokumentasi interaktif: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

## Isi data demo (opsional, biar leaderboard ada isinya)
```bash
python -m scripts.seed
# Membuat user demo (demo@diel.app / demo12345) + 2 strategi terverifikasi.
```

## Endpoint utama
| Method | Path | Keterangan |
|---|---|---|
| POST | `/auth/register` `/auth/login` | dapat JWT |
| GET  | `/auth/me` | profil (butuh token) |
| POST | `/strategies` | buat strategi (token) |
| GET  | `/strategies` | daftar strategi publik |
| GET  | `/strategies/{id}` | detail + spec + badge |
| POST | `/strategies/{id}/backtest` | jalankan backtest (token, pemilik) |
| POST | `/strategies/{id}/verify` | jalankan verifikasi berlapis (token, pemilik) |
| GET  | `/runs/{id}` | status + hasil/laporan run |
| GET  | `/strategies/{id}/equity` | equity curve untuk grafik |
| GET  | `/leaderboard` | strategi terurut skor verifikasi |

## Test
```bash
python -m pytest -q     # 7 test: alur auth -> strategi -> backtest/verify -> leaderboard
```

## Catatan arsitektur (Fase 2)
- Eksekusi backtest/verify pakai **BackgroundTasks** (cukup untuk lokal/MVP).
  Untuk skala produksi → worker **Redis/RQ** (BLUEPRINT §4), tanpa ubah kontrak API.
- Data backtest pakai **generator sintetis** (offline, deterministik). Integrasi
  **Dukascopy** (data forex nyata) sudah ada di engine, tinggal disambungkan ke API.
- Auth JWT HS256 stdlib; bisa diganti **Supabase Auth** saat produksi.
