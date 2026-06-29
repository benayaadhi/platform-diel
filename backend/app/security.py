"""Hashing password (PBKDF2) + JWT HS256 — semua stdlib, tanpa dependensi native.

Tanpa bcrypt/cryptography agar mudah jalan lokal & lolos environment minim.
Cukup untuk MVP; bisa di-upgrade / digantikan Supabase Auth saat produksi.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os

from .config import settings

_ITER = 200_000


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(signing_input: bytes) -> str:
    sig = hmac.new(settings.SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    return _b64url(sig)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITER)
    return f"pbkdf2_sha256${_ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_token(user_id: str) -> str:
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + settings.JWT_EXPIRE_MIN * 60,
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    return f"{h}.{p}.{_sign(signing_input)}"


def decode_token(token: str) -> str | None:
    try:
        h, p, sig = token.split(".")
        expected = _sign(f"{h}.{p}".encode())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64url_decode(p))
        if int(payload.get("exp", 0)) < int(dt.datetime.now(dt.timezone.utc).timestamp()):
            return None
        return payload.get("sub")
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
