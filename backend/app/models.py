"""Model ORM — mengikuti skema di docs/BLUEPRINT.md §7 (versi Fase 2).

Spec & hasil disimpan sebagai JSON (Text) agar fleksibel; di Postgres/Supabase
bisa dimigrasi ke kolom JSONB nanti tanpa ubah API.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Float, ForeignKey, Integer, String, Text, DateTime, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    handle: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategies: Mapped[list["Strategy"]] = relationship(back_populates="author")


class Strategy(Base):
    __tablename__ = "strategies"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    symbol: Mapped[str] = mapped_column(String(20))
    timeframe: Mapped[str] = mapped_column(String(8))
    spec_json: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(12), default="public")  # public|private
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped["User"] = relationship(back_populates="strategies")
    runs: Mapped[list["Run"]] = relationship(back_populates="strategy", cascade="all, delete-orphan")
    verification: Mapped["Verification | None"] = relationship(
        back_populates="strategy", uselist=False, cascade="all, delete-orphan"
    )


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), index=True)
    kind: Mapped[str] = mapped_column(String(12))             # backtest|verify
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|running|done|error
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    strategy: Mapped["Strategy"] = relationship(back_populates="runs")
    result: Mapped["RunResult | None"] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )


class RunResult(Base):
    __tablename__ = "run_results"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    equity_json: Mapped[str] = mapped_column(Text, default="[]")   # [{t, equity}] downsampled
    trades_json: Mapped[str] = mapped_column(Text, default="[]")
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # laporan verifikasi

    run: Mapped["Run"] = relationship(back_populates="result")


class Verification(Base):
    """Verifikasi terkini per strategi (untuk leaderboard & badge)."""
    __tablename__ = "verifications"
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), primary_key=True)
    badge: Mapped[str] = mapped_column(String(20), default="Unverified")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    report_json: Mapped[str] = mapped_column(Text, default="{}")
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategy: Mapped["Strategy"] = relationship(back_populates="verification")
