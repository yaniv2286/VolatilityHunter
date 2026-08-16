"""Aggregate real statistics from the daily trading loop logs.

Parses every ``logs/trading_YYYY-MM-DD.log`` (and legacy ``logs/VH_*.log``) file and
reports run reliability (pass/fail plus failure reasons), trade activity and
realized P&L over the full history covered by the log files.

Usage:
    python scripts/analyze_daily_logs.py [--logs-dir logs] [--out logs/daily_stats]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path

LOG_NAME_RE = re.compile(r"(?:trading|VH)_(\d{4}-\d{2}-\d{2})\.log$")
LINE_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})[.,]?\d*\s*[-|]?\s*(?P<rest>.*)$")

ENTRY_RE = re.compile(r"ENTRY (?P<ticker>[A-Z.\-]+): (?P<shares>[\d,]+) shares @ \$(?P<price>[\d,.]+)")
ENTERED_RE = re.compile(r"Entered (?P<ticker>[A-Z.\-]+): stop=\$(?P<stop>[\d,.]+)")
EXIT_RE = re.compile(
    r"EXIT (?P<ticker>[A-Z.\-]+): (?P<shares>[\d,]+) shares @ \$(?P<price>[\d,.]+)\s*\|\s*(?P<reason>.+?)\s*$"
)
EXITED_RE = re.compile(
    r"Exited (?P<ticker>[A-Z.\-]+): P&L=\$(?P<pnl>[+-]?[\d,.]+) \((?P<pct>[+-]?[\d,.]+)%\)"
)
COMPLETE_RE = re.compile(r"Daily loop complete in (?P<secs>[\d,.]+)s")
POSITIONS_RE = re.compile(r"Positions: (?P<n>\d+)")
EXITS_ENTRIES_RE = re.compile(r"Exits: (?P<exits>\d+) \| Entries: (?P<entries>\d+)")
EXIT_SIGNALS_RE = re.compile(r"Exit signals: (?P<n>\d+)")
CANDIDATES_RE = re.compile(r"Available slots: (?P<slots>\d+) \| Candidates: (?P<cands>\d+)")
ORDER_FAIL_RE = re.compile(r"(?:IBKR (?:buy|sell) order FAILED for|ORDER CANCEL:) (?P<ticker>[A-Z.\-]+)")

# Ordered: the first matching pattern is the reported failure reason for the run.
FAILURE_PATTERNS = [
    ("execution_lock", re.compile(r"EXECUTION LOCK DETECTED|Trading loop already ran today")),
    ("ibkr_connection", re.compile(r"IBKR connection (?:FAILED|error)|cannot proceed without IBKR")),
    ("cash_sanity_abort", re.compile(r"IBKR CASH SANITY CHECK FAILED|TRADING ABORTED")),
    ("market_closed", re.compile(r"MARKET CLOSED - Skipping order execution")),
    ("price_fetch", re.compile(r"Tiingo API failed|error in fetch_latest_prices")),
    ("gateway", re.compile(r"Gateway (?:failed|not running|login failed)|Ghost-Typist.*FAIL", re.I)),
    ("order_rejected", re.compile(r"order FAILED for|ORDER CANCEL:")),
    ("email", re.compile(r"Email send failed|Failed to send failure notification email")),
    ("fatal_exception", re.compile(r"CRITICAL ERROR in main trading loop|^FATAL:|Traceback")),
]


@dataclass
class Trade:
    ticker: str
    exit_date: str
    shares: int
    exit_price: float
    reason: str
    pnl: float | None = None
    pnl_pct: float | None = None


@dataclass
class RunDay:
    day: str
    started: bool = False
    completed: bool = False
    duration_s: float | None = None
    entries: list = field(default_factory=list)
    exits: list = field(default_factory=list)
    exit_signals: int | None = None
    candidates: int | None = None
    end_positions: int | None = None
    errors: int = 0
    warnings: int = 0
    failure_reasons: list = field(default_factory=list)
    order_failures: list = field(default_factory=list)


def parse_log(path: Path) -> RunDay:
    m = LOG_NAME_RE.search(path.name)
    day = m.group(1) if m else path.stem
    run = RunDay(day=day)
    pending_exit: dict[str, Trade] = {}

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip()
        lm = LINE_RE.match(line)
        body = lm.group("rest") if lm else line

        if "VOLATILITYHUNTER DAILY TRADING LOOP" in body:
            run.started = True
        if " ERROR " in line or line.strip().startswith("ERROR"):
            run.errors += 1
        if " WARNING " in line:
            run.warnings += 1

        for name, pat in FAILURE_PATTERNS:
            if pat.search(body) and name not in run.failure_reasons:
                run.failure_reasons.append(name)

        om = ORDER_FAIL_RE.search(body)
        if om:
            run.order_failures.append(om.group("ticker"))

        em = ENTRY_RE.search(body)
        if em:
            run.entries.append(
                {
                    "ticker": em.group("ticker"),
                    "shares": int(em.group("shares").replace(",", "")),
                    "price": float(em.group("price").replace(",", "")),
                }
            )

        xm = EXIT_RE.search(body)
        if xm:
            trade = Trade(
                ticker=xm.group("ticker"),
                exit_date=day,
                shares=int(xm.group("shares").replace(",", "")),
                exit_price=float(xm.group("price").replace(",", "")),
                reason=xm.group("reason").strip(),
            )
            pending_exit[trade.ticker] = trade
            run.exits.append(trade)

        pm = EXITED_RE.search(body)
        if pm:
            trade = pending_exit.get(pm.group("ticker"))
            if trade is None:
                trade = Trade(
                    ticker=pm.group("ticker"),
                    exit_date=day,
                    shares=0,
                    exit_price=0.0,
                    reason="unknown",
                )
                run.exits.append(trade)
            trade.pnl = float(pm.group("pnl").replace(",", ""))
            trade.pnl_pct = float(pm.group("pct").replace(",", ""))

        cm = COMPLETE_RE.search(body)
        if cm:
            run.completed = True
            run.duration_s = float(cm.group("secs").replace(",", ""))

        sm = EXIT_SIGNALS_RE.search(body)
        if sm:
            run.exit_signals = int(sm.group("n"))
        km = CANDIDATES_RE.search(body)
        if km:
            run.candidates = int(km.group("cands"))
        posm = POSITIONS_RE.search(body)
        if posm:
            run.end_positions = int(posm.group("n"))

    return run


def summarize(runs: list[RunDay]) -> dict:
    runs = sorted(runs, key=lambda r: r.day)
    trades = [t for r in runs for t in r.exits if t.pnl is not None]
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]

    passed = [r for r in runs if r.completed and not r.failure_reasons]
    degraded = [r for r in runs if r.completed and r.failure_reasons]
    failed = [r for r in runs if not r.completed]

    reason_counts = Counter(reason for r in runs for reason in r.failure_reasons)
    exit_reason_counts = Counter(t.reason for r in runs for t in r.exits)

    pnl_by_day: dict[str, float] = defaultdict(float)
    for t in trades:
        pnl_by_day[t.exit_date] += t.pnl

    def avg(values):
        return round(statistics.fmean(values), 4) if values else None

    days = [r.day for r in runs]
    calendar_days = 0
    if days:
        d0 = datetime.strptime(days[0], "%Y-%m-%d").date()
        d1 = datetime.strptime(days[-1], "%Y-%m-%d").date()
        calendar_days = (d1 - d0).days + 1

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "coverage": {
            "first_log_day": days[0] if days else None,
            "last_log_day": days[-1] if days else None,
            "log_files": len(runs),
            "calendar_days_spanned": calendar_days,
            "missing_days": sorted(
                set(
                    (date.fromordinal(o)).isoformat()
                    for o in range(
                        datetime.strptime(days[0], "%Y-%m-%d").date().toordinal(),
                        datetime.strptime(days[-1], "%Y-%m-%d").date().toordinal() + 1,
                    )
                )
                - set(days)
            )
            if days
            else [],
        },
        "runs": {
            "total": len(runs),
            "clean_pass": len(passed),
            "completed_with_errors": len(degraded),
            "failed_or_aborted": len(failed),
            "success_rate_pct": round(100 * len(passed) / len(runs), 2) if runs else None,
            "completion_rate_pct": round(100 * (len(passed) + len(degraded)) / len(runs), 2) if runs else None,
            "avg_duration_s": avg([r.duration_s for r in runs if r.duration_s is not None]),
            "failure_reason_counts": dict(reason_counts.most_common()),
            "failed_days": [{"day": r.day, "reasons": r.failure_reasons or ["no_completion_marker"]} for r in failed],
        },
        "trading": {
            "entries": sum(len(r.entries) for r in runs),
            "exits": sum(len(r.exits) for r in runs),
            "closed_trades_with_pnl": len(trades),
            "order_failures": sum(len(r.order_failures) for r in runs),
            "avg_exit_signals_per_run": avg([r.exit_signals for r in runs if r.exit_signals is not None]),
            "avg_candidates_per_run": avg([r.candidates for r in runs if r.candidates is not None]),
            "last_position_count": next((r.end_positions for r in reversed(runs) if r.end_positions is not None), None),
        },
        "pnl": {
            "win_rate_pct": round(100 * len(wins) / len(trades), 2) if trades else None,
            "wins": len(wins),
            "losses": len(losses),
            "total_realized_pnl": round(sum(t.pnl for t in trades), 2) if trades else 0.0,
            "avg_trade_pnl": avg([t.pnl for t in trades]),
            "avg_win_pnl": avg([t.pnl for t in wins]),
            "avg_loss_pnl": avg([t.pnl for t in losses]),
            "avg_trade_pct": avg([t.pnl_pct for t in trades]),
            "avg_win_pct": avg([t.pnl_pct for t in wins]),
            "avg_loss_pct": avg([t.pnl_pct for t in losses]),
            "profit_factor": round(
                sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses)), 3
            )
            if losses and sum(t.pnl for t in losses) != 0
            else None,
            "best_trade": max(
                ({"ticker": t.ticker, "day": t.exit_date, "pnl": t.pnl, "pct": t.pnl_pct} for t in trades),
                key=lambda x: x["pnl"],
                default=None,
            ),
            "worst_trade": min(
                ({"ticker": t.ticker, "day": t.exit_date, "pnl": t.pnl, "pct": t.pnl_pct} for t in trades),
                key=lambda x: x["pnl"],
                default=None,
            ),
            "exit_reason_counts": dict(exit_reason_counts.most_common()),
            "pnl_by_day": {d: round(v, 2) for d, v in sorted(pnl_by_day.items())},
        },
        "per_day": [asdict(r) | {"exits": [asdict(t) for t in r.exits]} for r in runs],
    }


def to_markdown(s: dict) -> str:
    cov, runs, trading, pnl = s["coverage"], s["runs"], s["trading"], s["pnl"]
    lines = [
        "# VolatilityHunter - real daily-run statistics",
        "",
        f"Generated {s['generated_at']}",
        "",
        "## Coverage",
        f"- Logs: {cov['log_files']} files, {cov['first_log_day']} -> {cov['last_log_day']} "
        f"({cov['calendar_days_spanned']} calendar days)",
        f"- Days with no log file: {len(cov['missing_days'])}",
        "",
        "## Run reliability",
        f"- Clean pass: {runs['clean_pass']}/{runs['total']} ({runs['success_rate_pct']}%)",
        f"- Completed with errors: {runs['completed_with_errors']}",
        f"- Failed / aborted: {runs['failed_or_aborted']}",
        f"- Average runtime: {runs['avg_duration_s']}s",
        "",
        "### Failure reasons",
    ]
    lines += [f"- {k}: {v}" for k, v in runs["failure_reason_counts"].items()] or ["- none"]
    lines += [
        "",
        "## Trading activity",
        f"- Entries: {trading['entries']} | Exits: {trading['exits']} | Order failures: {trading['order_failures']}",
        f"- Closed trades with P&L: {trading['closed_trades_with_pnl']}",
        "",
        "## Realized P&L",
        f"- Win rate: {pnl['win_rate_pct']}% ({pnl['wins']}W / {pnl['losses']}L)",
        f"- Total realized: ${pnl['total_realized_pnl']}",
        f"- Avg trade: ${pnl['avg_trade_pnl']} ({pnl['avg_trade_pct']}%)",
        f"- Avg win: ${pnl['avg_win_pnl']} ({pnl['avg_win_pct']}%) | Avg loss: ${pnl['avg_loss_pnl']} ({pnl['avg_loss_pct']}%)",
        f"- Profit factor: {pnl['profit_factor']}",
        f"- Best: {pnl['best_trade']}",
        f"- Worst: {pnl['worst_trade']}",
        "",
        "### Exit reasons",
    ]
    lines += [f"- {k}: {v}" for k, v in pnl["exit_reason_counts"].items()] or ["- none"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs-dir", default="logs")
    ap.add_argument("--out", default="logs/daily_stats")
    args = ap.parse_args()

    logs_dir = Path(args.logs_dir)
    files = sorted(p for p in logs_dir.rglob("*.log") if LOG_NAME_RE.search(p.name))
    if not files:
        raise SystemExit(f"No trading_YYYY-MM-DD.log / VH_YYYY-MM-DD.log files under {logs_dir}")

    summary = summarize([parse_log(p) for p in files])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = to_markdown(summary)
    out.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md)
    print(f"Wrote {out.with_suffix('.json')} and {out.with_suffix('.md')}")


if __name__ == "__main__":
    main()
