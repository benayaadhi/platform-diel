"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  getEquity, getRun, getStrategy, isLoggedIn, runBacktest, runVerify,
} from "@/lib/api";
import { EquityPoint, RunResult, StrategyDetail } from "@/lib/types";
import Badge from "@/components/Badge";
import EquityChart from "@/components/EquityChart";

function pct(x: any) {
  return typeof x === "number" ? `${(x * 100).toFixed(2)}%` : "—";
}
function num(x: any, d = 2) {
  return typeof x === "number" ? x.toFixed(d) : "—";
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-lg font-mono mt-0.5">{value}</div>
    </div>
  );
}

async function poll(runId: string, onUpdate: (r: RunResult) => void): Promise<RunResult> {
  for (let i = 0; i < 120; i++) {
    const r = await getRun(runId);
    onUpdate(r);
    if (r.status === "done" || r.status === "error") return r;
    await new Promise((res) => setTimeout(res, 1000));
  }
  throw new Error("Timeout menunggu hasil");
}

export default function StrategyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [strat, setStrat] = useState<StrategyDetail | null>(null);
  const [equity, setEquity] = useState<EquityPoint[]>([]);
  const [metrics, setMetrics] = useState<Record<string, any> | null>(null);
  const [report, setReport] = useState<Record<string, any> | null>(null);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const authed = isLoggedIn();

  const loadAll = useCallback(async () => {
    const s = await getStrategy(id);
    setStrat(s);
    const eq = await getEquity(id);
    setEquity(eq.points);
  }, [id]);

  useEffect(() => {
    loadAll().catch((e) => setError(e.message));
  }, [loadAll]);

  async function doRun(kind: "backtest" | "verify") {
    setBusy(true);
    setError(null);
    setStatus("Mengantri…");
    try {
      const start = kind === "backtest"
        ? await runBacktest(id, { bars: 6000, seed: 7 })
        : await runVerify(id, { bars: 6000, seed: 7, objective: "cagr_mdd" });
      const final = await poll(start.id, (r) => setStatus(`Status: ${r.status}…`));
      if (final.status === "error") {
        setError(final.error || "Run gagal");
      } else if (kind === "backtest") {
        setMetrics(final.metrics);
        const eq = await getEquity(id);
        setEquity(eq.points);
      } else {
        setReport(final.report || null);
        await loadAll(); // refresh badge
      }
      setStatus("");
    } catch (e: any) {
      setError(e.message);
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  if (error && !strat) {
    return <div className="card p-4 text-red-300 text-sm">Gagal: {error}</div>;
  }
  if (!strat) return <div className="text-slate-500 text-sm">Memuat…</div>;

  const wf = report?.walk_forward;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{strat.name}</h1>
          <p className="text-sm text-slate-400 mt-1">
            @{strat.author_handle} · {strat.symbol} {strat.timeframe}
          </p>
        </div>
        <div className="text-right">
          <Badge badge={strat.verification?.badge} />
          {strat.verification && (
            <div className="text-xs text-slate-400 mt-1">
              skor {strat.verification.score.toFixed(1)}/100
            </div>
          )}
        </div>
      </div>

      {authed ? (
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={() => doRun("backtest")} disabled={busy}>
            Jalankan Backtest
          </button>
          <button className="btn-primary" onClick={() => doRun("verify")} disabled={busy}>
            Verifikasi (badge)
          </button>
          {status && <span className="text-sm text-slate-400 self-center">{status}</span>}
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          Masuk untuk menjalankan backtest/verifikasi (hanya pemilik strategi).
        </p>
      )}

      {error && <div className="card p-3 text-sm text-red-300">{error}</div>}

      {/* Equity curve */}
      <section>
        <h2 className="text-sm font-semibold text-slate-300 mb-2">Equity Curve</h2>
        <div className="card p-4">
          <EquityChart points={equity} />
        </div>
      </section>

      {/* Metrics backtest */}
      {metrics && (
        <section>
          <h2 className="text-sm font-semibold text-slate-300 mb-2">Metrik Backtest</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Return" value={pct(metrics.total_return)} />
            <Stat label="CAGR" value={pct(metrics.cagr)} />
            <Stat label="Max Drawdown" value={pct(metrics.max_drawdown)} />
            <Stat label="Profit Factor" value={num(metrics.profit_factor)} />
            <Stat label="Trades" value={num(metrics.num_trades, 0)} />
            <Stat label="Win Rate" value={pct(metrics.win_rate)} />
            <Stat label="Sharpe" value={num(metrics.sharpe)} />
            <Stat label="Expectancy" value={num(metrics.expectancy)} />
          </div>
        </section>
      )}

      {/* Laporan verifikasi */}
      {report && (
        <section>
          <h2 className="text-sm font-semibold text-slate-300 mb-2">
            Laporan Verifikasi → <Badge badge={report.badge} /> (skor {num(report.score, 1)})
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="OOS Return" value={pct(report.oos_metrics?.total_return)} />
            <Stat label="OOS Max DD" value={pct(report.oos_metrics?.max_drawdown)} />
            <Stat label="PBO (overfit)" value={num(report.pbo)} />
            <Stat label="Robust region" value={pct(report.robust_fraction)} />
            {wf && <Stat label="WF Consistency" value={pct(wf.consistency)} />}
            {wf && <Stat label="WF Efficiency" value={num(wf.wf_efficiency)} />}
            <Stat label="Configs diuji" value={num(report.n_configs, 0)} />
            <Stat label="OOS Trades" value={num(report.oos_metrics?.num_trades, 0)} />
          </div>
          {Array.isArray(report.notes) && report.notes.length > 0 && (
            <p className="text-xs text-slate-500 mt-2">Catatan: {report.notes.join("; ")}</p>
          )}
        </section>
      )}

      {/* Spec */}
      <section>
        <h2 className="text-sm font-semibold text-slate-300 mb-2">Spec</h2>
        <pre className="card p-4 text-xs overflow-x-auto text-slate-300">
          {JSON.stringify(strat.spec, null, 2)}
        </pre>
      </section>
    </div>
  );
}
