"""Isi DB dengan data demo supaya leaderboard tidak kosong saat cek lokal.

Jalankan:  python -m scripts.seed
(idempotent-ish: aman dijalankan ulang; user demo dibuat jika belum ada)
"""
from __future__ import annotations

import json

from app.db import SessionLocal, init_db
from app.engine_runner import execute_run
from app.models import Run, Strategy, User
from app.security import hash_password

DEMO_USER = {"handle": "diel_demo", "email": "demo@diel.app", "password": "demo12345"}

STRATEGIES = [
    {
        "name": "EMA Cross 20/50",
        "indicators": [
            {"id": "ema_fast", "type": "EMA", "period": 20},
            {"id": "ema_slow", "type": "EMA", "period": 50},
        ],
        "entry_long": "cross_over(ema_fast, ema_slow)",
        "entry_short": "cross_under(ema_fast, ema_slow)",
        "exit_long": "cross_under(ema_fast, ema_slow)",
        "exit_short": "cross_over(ema_fast, ema_slow)",
        "stop_loss": {"type": "atr", "mult": 2.0, "atr_period": 14},
        "take_profit": {"type": "rr", "ratio": 1.5},
        "risk": {"per_trade_pct": 1.0},
        "param_grid": {
            "indicators.ema_fast.period": [10, 15, 20],
            "indicators.ema_slow.period": [40, 50, 60],
            "stop_loss.mult": [1.5, 2.0, 2.5],
        },
    },
    {
        "name": "RSI Reversion",
        "indicators": [{"id": "rsi", "type": "RSI", "period": 14}],
        "entry_long": "cross_over(rsi, 30)",
        "entry_short": "cross_under(rsi, 70)",
        "exit_long": "cross_over(rsi, 55)",
        "exit_short": "cross_under(rsi, 45)",
        "stop_loss": {"type": "pips", "pips": 30},
        "take_profit": {"type": "rr", "ratio": 1.2},
        "risk": {"per_trade_pct": 1.0},
        "param_grid": {"stop_loss.pips": [20, 30, 40]},
    },
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=DEMO_USER["email"]).first()
        if not user:
            user = User(handle=DEMO_USER["handle"], email=DEMO_USER["email"],
                        password_hash=hash_password(DEMO_USER["password"]))
            db.add(user)
            db.commit()
            print(f"User demo dibuat: {DEMO_USER['email']} / {DEMO_USER['password']}")

        run_ids = []
        for s in STRATEGIES:
            spec = {**s, "symbol": "EURUSD", "timeframe": "H1"}
            strat = Strategy(author_id=user.id, name=s["name"], symbol="EURUSD",
                             timeframe="H1", spec_json=json.dumps(spec), visibility="public")
            db.add(strat)
            db.commit()
            run = Run(strategy_id=strat.id, kind="verify",
                      params_json=json.dumps({"bars": 6000, "seed": 7}))
            db.add(run)
            db.commit()
            run_ids.append(run.id)
            print(f"Strategi dibuat: {s['name']} ({strat.id})")
    finally:
        db.close()

    # Jalankan verifikasi (sinkron) supaya leaderboard langsung terisi.
    for rid in run_ids:
        execute_run(rid)
        print(f"Verifikasi selesai untuk run {rid}")
    print("Seed selesai. Jalankan API & buka frontend untuk lihat leaderboard.")


if __name__ == "__main__":
    main()
