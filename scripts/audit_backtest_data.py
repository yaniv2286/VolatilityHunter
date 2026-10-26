"""Read-only inventory of local Tiingo data for choosing a backtest window.

This checks local coverage and basic integrity, not historical universe
completeness or correctness against the provider. Never imports a broker,
fetches prices, or modifies portfolio/data files.
"""

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
logger = logging.getLogger(__name__)


def audit(root=ROOT):
    tickers = list(dict.fromkeys(
        line.strip().upper()
        for line in (root / "tickers.txt").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ))
    counts, starts, ends, coverage, schemas = (
        Counter(), Counter(), Counter(), Counter(), Counter()
    )
    missing, errors, examples, quality_issues = [], [], [], []
    for number, ticker in enumerate(tickers, 1):
        path = root / "data" / f"{ticker}.parquet"
        if not path.exists():
            missing.append(ticker)
            continue
        try:
            parquet = pq.ParquetFile(path)
            names = parquet.schema_arrow.names
            schemas[tuple(names)] += 1
            metadata = json.loads(
                (parquet.schema_arrow.metadata or {}).get(b"pandas", b"{}")
            )
            index_names = [
                name for name in metadata.get("index_columns", [])
                if isinstance(name, str)
            ]
            date_column = next(
                (name for name in ["date", "Date"] + index_names if name in names),
                None,
            )
            if date_column is None:
                raise ValueError("No stored date/index column")
            columns = list(dict.fromkeys([date_column] + [
                name for name in
                ("close", "adjClose", "volume", "divCash", "splitFactor")
                if name in names
            ]))
            frame = parquet.read(columns=columns).to_pandas()
            dates = pd.DatetimeIndex(pd.to_datetime(
                frame[date_column] if date_column in frame else frame.index
            ))
            if dates.tz is not None:
                dates = dates.tz_localize(None)
            if frame.empty or dates.isna().all():
                raise ValueError("No dated observations")
            counts["readable_files"] += 1
            counts["rows"] += len(frame)
            counts["under_300_rows"] += int(len(frame) < 300)
            issues = []
            for label, condition in (
                ("duplicate_dates", dates.has_duplicates),
                ("unsorted_dates", not dates.is_monotonic_increasing),
                ("null_dates", dates.isna().any()),
            ):
                counts[f"files_{label}"] += int(condition)
                if condition:
                    issues.append(label)
            start, end = str(dates.min().date()), str(dates.max().date())
            starts[start] += 1
            ends[end] += 1
            for year in (1998, 1999, 2000, 2001, 2008, 2020, 2022):
                cutoff = pd.Timestamp(year, 1, 1)
                coverage[f"start_before_{year}"] += int(dates.min() < cutoff)
                coverage[f"at_least_252_rows_before_{year}"] += int(
                    (dates < cutoff).sum() >= 252
                )
            for column in ("close", "adjClose"):
                bad = column not in frame or bool(
                    (frame[column].isna() | (frame[column] <= 0)).any()
                )
                counts[f"files_missing_or_bad_{column}"] += int(bad)
                if bad:
                    issues.append(f"missing_or_bad_{column}")
            counts["files_all_adjusted_ohlcv"] += int(all(
                name in names for name in
                ("adjOpen", "adjHigh", "adjLow", "adjClose", "adjVolume")
            ))
            counts["files_dividend_and_split_columns"] += int(all(
                name in names for name in ("divCash", "splitFactor")
            ))
            for column, neutral, label in (
                ("divCash", 0, "files_nonzero_dividends"),
                ("splitFactor", 1, "files_nonunit_splits"),
            ):
                counts[label] += int(
                    column in frame and (frame[column].fillna(neutral) != neutral).any()
                )
            if issues:
                quality_issues.append({"ticker": ticker, "issues": issues})
            if ticker in ("AAPL", "MSFT", "SPY", "NVDA"):
                examples.append({
                    "ticker": ticker, "start": start, "end": end,
                    "rows": len(frame), "columns": names,
                })
        except Exception:
            logger.exception("Unable to audit %s", ticker)
            errors.append(ticker)
        if number % 500 == 0:
            logger.info("Inspected %s/%s tickers", number, len(tickers))
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "current tickers.txt; local files only",
        "historical_universe_validated": False,
        "universe_count": len(tickers),
        "summary": dict(counts),
        "history_coverage": dict(coverage),
        "most_common_first_dates": starts.most_common(8),
        "most_common_last_dates": ends.most_common(8),
        "missing_files": missing,
        "read_errors": errors,
        "quality_issues": quality_issues,
        "examples": examples,
        "schema_variants": len(schemas),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = audit()
    print(json.dumps(result, indent=2))
    # Missing files and coverage limitations are reported, never treated as
    # proof that a historical universe is complete.
    raise SystemExit(1 if result["read_errors"] or result["quality_issues"] else 0)
