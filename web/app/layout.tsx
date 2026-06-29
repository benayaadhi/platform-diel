import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "DIEL — Verified Trading Strategies",
  description:
    "Marketplace & sosial untuk strategi trading yang benar-benar terverifikasi (backtest + walk-forward + anti-overfit).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>
        <Nav />
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-5xl px-4 py-10 text-xs text-slate-600">
          Past performance is not indicative of future results. Bukan nasihat finansial.
        </footer>
      </body>
    </html>
  );
}
