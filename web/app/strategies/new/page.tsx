"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createStrategy, isLoggedIn } from "@/lib/api";

const EXAMPLE_SPEC = `{
  "indicators": [
    { "id": "ema_fast", "type": "EMA", "source": "close", "period": 20 },
    { "id": "ema_slow", "type": "EMA", "source": "close", "period": 50 }
  ],
  "entry_long":  "cross_over(ema_fast, ema_slow)",
  "entry_short": "cross_under(ema_fast, ema_slow)",
  "exit_long":   "cross_under(ema_fast, ema_slow)",
  "exit_short":  "cross_over(ema_fast, ema_slow)",
  "stop_loss":   { "type": "atr", "mult": 2.0, "atr_period": 14 },
  "take_profit": { "type": "rr", "ratio": 1.5 },
  "risk":        { "per_trade_pct": 1.0 },
  "param_grid": {
    "indicators.ema_fast.period": [10, 15, 20, 25],
    "indicators.ema_slow.period": [40, 50, 60],
    "stop_loss.mult": [1.5, 2.0, 2.5]
  }
}`;

export default function NewStrategyPage() {
  const router = useRouter();
  const [name, setName] = useState("EMA Cross 20/50");
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [specText, setSpecText] = useState(EXAMPLE_SPEC);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) router.push("/login");
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    let spec: Record<string, any>;
    try {
      spec = JSON.parse(specText);
    } catch {
      setError("Spec bukan JSON valid.");
      return;
    }
    setBusy(true);
    try {
      const s = await createStrategy({ name, symbol, timeframe, spec });
      router.push(`/strategies/${s.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-1">Buat Strategi</h1>
      <p className="text-sm text-slate-400 mb-4">
        Deskripsikan strategi sebagai spec (DSL). Setelah dibuat, jalankan
        backtest & verifikasi untuk dapat badge.
      </p>
      <form onSubmit={submit} className="card p-5 space-y-4">
        <div>
          <label className="label">Nama</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Symbol</label>
            <input className="input" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
          </div>
          <div>
            <label className="label">Timeframe</label>
            <select className="input" value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
              {["M5", "M15", "M30", "H1", "H4", "D1"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="label">Spec (JSON)</label>
          <textarea
            className="input font-mono text-xs h-72"
            value={specText}
            onChange={(e) => setSpecText(e.target.value)}
            spellCheck={false}
          />
          <p className="text-xs text-slate-500 mt-1">
            Fungsi sinyal: <code>cross_over</code>, <code>cross_under</code>,{" "}
            <code>rising</code>, <code>falling</code>, perbandingan & and/or.
            Indikator: EMA, SMA, ATR, RSI. <code>param_grid</code> dipakai untuk
            optimisasi & deteksi overfit.
          </p>
        </div>
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button className="btn-primary" disabled={busy}>
          {busy ? "Menyimpan…" : "Buat strategi"}
        </button>
      </form>
    </div>
  );
}
