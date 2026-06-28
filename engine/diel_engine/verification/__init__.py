"""Verification layer (Fase 1) — JANTUNG kredibilitas Platform-DIEL.

Backtest in-sample saja = bukti lemah. Lapisan ini menambahkan gerbang yang
sulit dipalsukan:
- split in-sample / out-of-sample (OOS ditetapkan platform, bukan author),
- optimisasi parameter di IS lalu diuji di OOS,
- walk-forward analysis (konsistensi lintas waktu),
- deteksi overfit (PBO via CSCV + fraksi region yang robust),
- skor 0..100 + level badge.

Lihat docs/BLUEPRINT.md §6.
"""
