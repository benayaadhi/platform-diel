"""Skema Pydantic (request/response API)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ---- auth ----
class RegisterIn(BaseModel):
    handle: str = Field(min_length=3, max_length=40)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    handle: str
    email: EmailStr


# ---- strategies ----
class StrategyIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    symbol: str
    timeframe: str
    spec: dict[str, Any]           # spec DSL penuh (boleh berisi param_grid)
    visibility: str = "public"


class VerificationOut(BaseModel):
    badge: str
    score: float


class StrategyOut(BaseModel):
    id: str
    name: str
    symbol: str
    timeframe: str
    author_handle: str
    visibility: str
    verification: Optional[VerificationOut] = None


class StrategyDetailOut(StrategyOut):
    spec: dict[str, Any]


# ---- runs ----
class RunRequest(BaseModel):
    # Data sintetis untuk MVP lokal (tanpa jaringan). Dukascopy menyusul.
    bars: int = 4000
    seed: int = 42
    objective: str = "cagr_mdd"        # khusus verify


class RunOut(BaseModel):
    id: str
    strategy_id: str
    kind: str
    status: str
    error: Optional[str] = None


class RunResultOut(RunOut):
    metrics: dict[str, Any] = {}
    report: Optional[dict[str, Any]] = None
