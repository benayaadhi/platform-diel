import { EquityPoint } from "@/lib/types";

// Grafik garis SVG ringan (tanpa dependency). Cukup untuk visualisasi equity curve.
export default function EquityChart({ points }: { points: EquityPoint[] }) {
  if (!points || points.length < 2) {
    return (
      <div className="text-sm text-slate-500 py-10 text-center">
        Belum ada data equity. Jalankan backtest dulu.
      </div>
    );
  }

  const W = 760;
  const H = 240;
  const pad = 8;
  const vals = points.map((p) => p.equity);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;

  const x = (i: number) => pad + (i / (points.length - 1)) * (W - 2 * pad);
  const y = (v: number) => H - pad - ((v - min) / range) * (H - 2 * pad);

  const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.equity).toFixed(1)}`).join(" ");
  const up = vals[vals.length - 1] >= vals[0];
  const stroke = up ? "#34d399" : "#f87171";
  const fill = up ? "#34d39922" : "#f8717122";
  const area = `${d} L ${x(points.length - 1).toFixed(1)} ${H - pad} L ${x(0).toFixed(1)} ${H - pad} Z`;

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="none">
        <path d={area} fill={fill} />
        <path d={d} fill="none" stroke={stroke} strokeWidth={2} />
      </svg>
      <div className="flex justify-between text-xs text-slate-500 mt-1">
        <span>{new Date(points[0].t).toLocaleDateString()}</span>
        <span>
          {min.toFixed(0)} – {max.toFixed(0)}
        </span>
        <span>{new Date(points[points.length - 1].t).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
