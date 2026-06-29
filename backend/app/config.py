"""Konfigurasi via environment variable (dengan default dev yang aman dijalankan).

Lokal (default)  : SQLite file, zero-setup.
Produksi/Supabase: set DATABASE_URL ke connection string Postgres Supabase.
"""
from __future__ import annotations

import os


class Settings:
    # Default SQLite lokal -> bisa langsung jalan tanpa daftar akun apa pun.
    # Untuk Supabase: postgresql+psycopg://USER:PASS@HOST:5432/postgres
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./diel.db")

    # WAJIB diganti di produksi (set env SECRET_KEY).
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MIN: int = int(os.environ.get("JWT_EXPIRE_MIN", "10080"))  # 7 hari

    # CORS untuk frontend Next.js (Vercel/local).
    CORS_ORIGINS: list[str] = os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")

    # Batas aman ukuran backtest dari API (anti abuse).
    MAX_BARS: int = int(os.environ.get("MAX_BARS", "20000"))


settings = Settings()
