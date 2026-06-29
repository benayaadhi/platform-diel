"""Leaderboard: strategi terverifikasi terurut skor (bagian 'flex')."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Strategy, Verification
from ..schemas import StrategyOut, VerificationOut

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=list[StrategyOut])
def leaderboard(db: Session = Depends(get_db), limit: int = 50):
    rows = db.execute(
        select(Strategy, Verification)
        .join(Verification, Verification.strategy_id == Strategy.id)
        .options(joinedload(Strategy.author))
        .where(Strategy.visibility == "public")
        .order_by(desc(Verification.score))
        .limit(min(limit, 200))
    ).all()
    out = []
    for s, v in rows:
        out.append(StrategyOut(
            id=s.id, name=s.name, symbol=s.symbol, timeframe=s.timeframe,
            author_handle=s.author.handle, visibility=s.visibility,
            verification=VerificationOut(badge=v.badge, score=v.score),
        ))
    return out
