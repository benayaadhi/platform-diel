const STYLES: Record<string, string> = {
  Robust: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  Backtested: "bg-blue-500/15 text-blue-300 border-blue-500/40",
  Unverified: "bg-slate-500/15 text-slate-400 border-slate-500/40",
};

const LABELS: Record<string, string> = {
  Robust: "🟩 Robust",
  Backtested: "🟦 Backtested",
  Unverified: "⬜ Unverified",
};

export default function Badge({ badge }: { badge?: string | null }) {
  const key = badge && STYLES[badge] ? badge : "Unverified";
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${STYLES[key]}`}>
      {LABELS[key]}
    </span>
  );
}
