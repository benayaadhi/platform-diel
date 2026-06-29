"""Endpoint strategi: buat, daftar (publik), detail, jalankan backtest/verify."""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..engine_runner import execute_run
from ..models import Run, Strategy, User
from ..schemas import (
    RunOut, RunRequest, StrategyDetailOut, StrategyIn, StrategyOut, VerificationOut,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _to_out(s: Strategy) -> StrategyOut:
    ver = None
    if s.verification:
        ver = VerificationOut(badge=s.verification.badge, score=s.verification.score)
    return StrategyOut(
        id=s.id, name=s.name, symbol=s.symbol, timeframe=s.timeframe,
        author_handle=s.author.handle, visibility=s.visibility, verification=ver,
    )


def _validate_spec(spec: dict, symbol: str, timeframe: str) -> None:
    from diel_engine.strategy.spec import spec_from_dict
    payload = {**spec, "symbol": symbol, "timeframe": timeframe}
    try:
        spec_from_dict(payload)  # melempar ValueError kalau tidak valid
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Spec tidak valid: {e}")


@router.post("", response_model=StrategyDetailOut, status_code=201)
def create_strategy(body: StrategyIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    _validate_spec(body.spec, body.symbol, body.timeframe)
    spec = {**body.spec, "name": body.name, "symbol": body.symbol, "timeframe": body.timeframe}
    s = Strategy(author_id=user.id, name=body.name, symbol=body.symbol.upper(),
                 timeframe=body.timeframe.upper(), spec_json=json.dumps(spec),
                 visibility=body.visibility)
    db.add(s)
    db.commit()
    db.refresh(s)
    out = _to_out(s)
    return StrategyDetailOut(**out.model_dump(), spec=spec)


@router.get("", response_model=list[StrategyOut])
def list_strategies(db: Session = Depends(get_db), limit: int = 50):
    rows = db.scalars(
        select(Strategy)
        .options(joinedload(Strategy.author), joinedload(Strategy.verification))
        .where(Strategy.visibility == "public")
        .limit(min(limit, 200))
    ).all()
    return [_to_out(s) for s in rows]


@router.get("/{strategy_id}", response_model=StrategyDetailOut)
def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    s = db.get(Strategy, strategy_id)
    if not s or s.visibility != "public":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Strategi tidak ditemukan")
    out = _to_out(s)
    return StrategyDetailOut(**out.model_dump(), spec=json.loads(s.spec_json))


def _start_run(kind: str, strategy_id: str, body: RunRequest,
               db: Session, user: User, bg: BackgroundTasks) -> RunOut:
    s = db.get(Strategy, strategy_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Strategi tidak ditemukan")
    if s.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bukan pemilik strategi")
    if body.bars > settings.MAX_BARS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"bars melebihi batas {settings.MAX_BARS}")
    run = Run(strategy_id=strategy_id, kind=kind, status="pending",
              params_json=body.model_dump_json())
    db.add(run)
    db.commit()
    db.refresh(run)
    bg.add_task(execute_run, run.id)
    return RunOut(id=run.id, strategy_id=strategy_id, kind=kind, status=run.status)


@router.post("/{strategy_id}/backtest", response_model=RunOut, status_code=202)
def run_backtest_ep(strategy_id: str, body: RunRequest, bg: BackgroundTasks,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _start_run("backtest", strategy_id, body, db, user, bg)


@router.post("/{strategy_id}/verify", response_model=RunOut, status_code=202)
def run_verify_ep(strategy_id: str, body: RunRequest, bg: BackgroundTasks,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _start_run("verify", strategy_id, body, db, user, bg)
