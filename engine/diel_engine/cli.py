"""CLI Fase 0: jalankan satu strategi end-to-end.

Contoh:
  # data sintetis (offline, deterministik) — bukti engine jalan
  python -m diel_engine.cli backtest --strategy examples/ema_cross.json \
      --data synthetic --bars 3000 --seed 7

  # data CSV (timestamp,open,high,low,close,volume)
  python -m diel_engine.cli backtest --strategy examples/ema_cross.json \
      --data csv --csv path/to/EURUSD_H1.csv

  # data nyata Dukascopy (butuh jaringan)
  python -m diel_engine.cli backtest --strategy examples/ema_cross.json \
      --data dukascopy --start 2023-01-01 --end 2023-02-01
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from .backtest.costs import CostModel
from .backtest.engine import run_backtest
from .data.loaders import load_csv, synthetic_bars
from .strategy.spec import load_spec


def _load_bars(args, spec):
    if args.data == "synthetic":
        return synthetic_bars(spec.symbol, spec.timeframe, n=args.bars, seed=args.seed)
    if args.data == "csv":
        if not args.csv:
            sys.exit("--csv wajib untuk --data csv")
        return load_csv(args.csv, spec.symbol, spec.timeframe)
    if args.data == "dukascopy":
        from .data.dukascopy import download_bars
        start = dt.datetime.fromisoformat(args.start).replace(tzinfo=dt.timezone.utc)
        end = dt.datetime.fromisoformat(args.end).replace(tzinfo=dt.timezone.utc)
        return download_bars(spec.symbol, spec.timeframe, start, end)
    sys.exit(f"sumber data tidak dikenal: {args.data}")


def cmd_backtest(args) -> None:
    spec = load_spec(args.strategy)
    bars = _load_bars(args, spec)
    costs = CostModel(
        spread_pips=args.spread,
        commission_per_lot=args.commission,
    )
    result = run_backtest(bars, spec, initial_balance=args.balance, costs=costs)

    print(f"Bars     : {len(bars)}  "
          f"({bars.index[0].date()} -> {bars.index[-1].date()})")
    print(result.summary())

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[hasil JSON -> {args.json_out}]")
    if args.equity_out:
        result.equity_curve.to_csv(args.equity_out, header=True)
        print(f"[equity curve -> {args.equity_out}]")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="diel_engine", description="Platform-DIEL backtest engine (Fase 0)")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backtest", help="jalankan backtest satu strategi")
    b.add_argument("--strategy", required=True, help="path file spec JSON")
    b.add_argument("--data", default="synthetic", choices=["synthetic", "csv", "dukascopy"])
    b.add_argument("--csv", help="path CSV untuk --data csv")
    b.add_argument("--bars", type=int, default=3000, help="jumlah bar (synthetic)")
    b.add_argument("--seed", type=int, default=42, help="seed (synthetic)")
    b.add_argument("--start", help="ISO date (dukascopy)")
    b.add_argument("--end", help="ISO date (dukascopy)")
    b.add_argument("--balance", type=float, default=10_000.0)
    b.add_argument("--spread", type=float, default=1.0, help="spread (pips)")
    b.add_argument("--commission", type=float, default=3.5, help="komisi per lot per sisi")
    b.add_argument("--json-out", dest="json_out", help="tulis hasil lengkap ke JSON")
    b.add_argument("--equity-out", dest="equity_out", help="tulis equity curve ke CSV")
    b.set_defaults(func=cmd_backtest)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
