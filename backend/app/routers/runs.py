"""Endpoint run: status + hasil, dan equity curve untuk chart."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Run, RunResult
from ..schemas import RunResultOut

router = APIRouter(tags=["runs"])


@router.get("/runs/{run_id}", response_model=RunResultOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run tidak ditemukan")
    metrics, report = {}, None
    res = db.get(RunResult, run_id)
    if res:
        metrics = json.loads(res.metrics_json or "{}")
        report = json.loads(res.report_json) if res.report_json else None
    return RunResultOut(
        id=run.id, strategy_id=run.strategy_id, kind=run.kind,
        status=run.status, error=run.error, metrics=metrics, report=report,
    )


@router.get("/strategies/{strategy_id}/equity")
def get_equity(strategy_id: str, db: Session = Depends(get_db)):
    """Equity curve dari backtest sukses terbaru (untuk grafik di frontend)."""
    run = db.scalar(
        select(Run).where(Run.strategy_id == strategy_id, Run.kind == "backtest",
                          Run.status == "done").order_by(desc(Run.finished_at))
    )
    if not run:
        return {"points": []}
    res = db.get(RunResult, run.id)
    return {"points": json.loads(res.equity_json) if res else []}
