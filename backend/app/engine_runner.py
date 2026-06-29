"""Jembatan ke diel_engine: jalankan backtest/verify lalu simpan hasil ke DB.

Dijalankan sebagai background task. Untuk MVP lokal eksekusi sinkron di thread
pool; di Fase 3 dipindah ke worker Redis/RQ (lihat BLUEPRINT §4) tanpa ubah API.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np

from diel_engine.backtest.engine import run_backtest
from diel_engine.data.loaders import synthetic_bars
from diel_engine.strategy.spec import spec_from_dict
from diel_engine.verification.verify import verify_strategy

from .db import SessionLocal
from .models import Run, RunResult, Strategy, Verification


def _downsample_equity(equity, max_points: int = 500):
    n = len(equity)
    step = max(1, n // max_points)
    out = []
    for i in range(0, n, step):
        ts = equity.index[i]
        out.append({"t": ts.isoformat(), "equity": round(float(equity.iloc[i]), 2)})
    return out


def execute_run(run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return
        run.status = "running"
        db.commit()

        strat = db.get(Strategy, run.strategy_id)
        spec_dict = json.loads(strat.spec_json)
        params = json.loads(run.params_json or "{}")
        bars = synthetic_bars(
            strat.symbol, strat.timeframe,
            n=int(params.get("bars", 4000)), seed=int(params.get("seed", 42)),
        )

        result = db.get(RunResult, run_id) or RunResult(run_id=run_id)

        if run.kind == "backtest":
            spec = spec_from_dict(spec_dict)
            res = run_backtest(bars, spec)
            result.metrics_json = json.dumps(res.metrics)
            result.equity_json = json.dumps(_downsample_equity(res.equity_curve))
            result.trades_json = json.dumps([t.to_dict() for t in res.trades])
            result.report_json = None
        elif run.kind == "verify":
            report = verify_strategy(
                bars, spec_dict, objective=params.get("objective", "cagr_mdd"),
            )
            result.metrics_json = json.dumps(report.oos_metrics)
            result.report_json = json.dumps(report.to_dict())
            # Upsert verifikasi terkini strategi (untuk leaderboard/badge).
            ver = db.get(Verification, strat.id) or Verification(strategy_id=strat.id)
            ver.badge = report.badge
            ver.score = float(report.score)
            ver.report_json = result.report_json
            ver.computed_at = dt.datetime.now(dt.timezone.utc)
            db.merge(ver)
        else:
            raise ValueError(f"jenis run tidak dikenal: {run.kind}")

        db.merge(result)
        run.status = "done"
        run.finished_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    except Exception as e:  # noqa: BLE001 — simpan error ke DB untuk diagnosa
        db.rollback()
        run = db.get(Run, run_id)
        if run is not None:
            run.status = "error"
            run.error = f"{type(e).__name__}: {e}"
            run.finished_at = dt.datetime.now(dt.timezone.utc)
            db.commit()
    finally:
        db.close()
