"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getLeaderboard } from "@/lib/api";
import { Strategy } from "@/lib/types";
import Badge from "@/components/Badge";

export default function Home() {
  const [rows, setRows] = useState<Strategy[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLeaderboard()
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <p className="text-sm text-slate-400 mt-1">
          Strategi terurut <span className="text-slate-200">skor verifikasi</span> —
          backtest in-sample, out-of-sample, walk-forward, & deteksi overfit (PBO).
          Badge tinggi = sulit dipalsukan.
        </p>
      </div>

      {error && (
        <div className="card p-4 text-sm text-red-300 mb-4">
          Gagal memuat: {error}
          <div className="text-slate-500 mt-1">
            Pastikan backend jalan di <code>http://localhost:8000</code>.
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-slate-500 text-sm">Memuat…</div>
      ) : rows.length === 0 ? (
        <div className="card p-8 text-center text-slate-400">
          Belum ada strategi terverifikasi.{" "}
          <Link href="/strategies/new" className="text-accent underline">
            Buat strategi pertama
          </Link>{" "}
          atau jalankan <code>python -m scripts.seed</code> di backend.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-left text-slate-400 border-b border-edge">
              <tr>
                <th className="px-4 py-3 w-10">#</th>
                <th className="px-4 py-3">Strategi</th>
                <th className="px-4 py-3">Author</th>
                <th className="px-4 py-3">Pair</th>
                <th className="px-4 py-3">Badge</th>
                <th className="px-4 py-3 text-right">Skor</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s, i) => (
                <tr key={s.id} className="border-b border-edge/50 hover:bg-edge/30">
                  <td className="px-4 py-3 text-slate-500">{i + 1}</td>
                  <td className="px-4 py-3">
                    <Link href={`/strategies/${s.id}`} className="font-medium hover:text-accent">
                      {s.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-400">@{s.author_handle}</td>
                  <td className="px-4 py-3 text-slate-400">
                    {s.symbol} {s.timeframe}
                  </td>
                  <td className="px-4 py-3">
                    <Badge badge={s.verification?.badge} />
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {s.verification ? s.verification.score.toFixed(1) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
