"""Test alur penuh API: auth -> strategi -> backtest -> verify -> leaderboard.

BackgroundTasks dieksekusi oleh TestClient sebelum respons kembali, jadi run
sudah 'done' saat di-GET.
"""

EMA_SPEC = {
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
        "indicators.ema_fast.period": [10, 20],
        "stop_loss.mult": [1.5, 2.5],
    },
}


def _create(client, headers, name="EMA Cross"):
    return client.post("/strategies", headers=headers, json={
        "name": name, "symbol": "EURUSD", "timeframe": "H1", "spec": EMA_SPEC,
    })


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_auth_required_for_create(client):
    assert _create(client, {}).status_code == 401


def test_register_duplicate_rejected(client):
    client.post("/auth/register", json={"handle": "dup", "email": "d@e.com", "password": "secret1"})
    r = client.post("/auth/register", json={"handle": "dup", "email": "d@e.com", "password": "secret1"})
    assert r.status_code == 409


def test_invalid_spec_rejected(client, auth_headers):
    r = client.post("/strategies", headers=auth_headers, json={
        "name": "bad", "symbol": "EURUSD", "timeframe": "H1",
        "spec": {"indicators": []},  # tanpa entry -> invalid
    })
    assert r.status_code == 422


def test_full_backtest_flow(client, auth_headers):
    sid = _create(client, auth_headers, "BT Flow").json()["id"]
    r = client.post(f"/strategies/{sid}/backtest", headers=auth_headers,
                    json={"bars": 2000, "seed": 7})
    assert r.status_code == 202
    run_id = r.json()["id"]

    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "done", run
    assert "num_trades" in run["metrics"]

    eq = client.get(f"/strategies/{sid}/equity").json()
    assert len(eq["points"]) > 0
    assert "equity" in eq["points"][0]


def test_full_verify_flow_and_leaderboard(client, auth_headers):
    sid = _create(client, auth_headers, "Verify Flow").json()["id"]
    r = client.post(f"/strategies/{sid}/verify", headers=auth_headers,
                    json={"bars": 3000, "seed": 7})
    assert r.status_code == 202
    run = client.get(f"/runs/{r.json()['id']}").json()
    assert run["status"] == "done", run
    assert run["report"] is not None
    assert "badge" in run["report"] and "score" in run["report"]

    # strategi sekarang punya verifikasi -> muncul di detail & leaderboard
    detail = client.get(f"/strategies/{sid}").json()
    assert detail["verification"] is not None
    lb = client.get("/leaderboard").json()
    assert any(s["id"] == sid for s in lb)


def test_non_owner_cannot_run(client, auth_headers):
    sid = _create(client, auth_headers, "Owned").json()["id"]
    other = client.post("/auth/register", json={
        "handle": "intruder", "email": "x@e.com", "password": "secret1"}).json()["access_token"]
    r = client.post(f"/strategies/{sid}/backtest",
                    headers={"Authorization": f"Bearer {other}"}, json={"bars": 500})
    assert r.status_code == 403
