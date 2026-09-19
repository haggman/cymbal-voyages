#!/usr/bin/env python3
"""
Run the walkthrough queries locally with DuckDB over out/ (no Google Cloud needed) and print the
results as Markdown tables. `--write` renders docs/anomaly-walkthrough.md from the results.

The queries are written for BigQuery; a small set of textual rewrites makes them run on DuckDB.
Any query that needs more than these rewrites is kept out of the trail on purpose.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from walkthrough_queries import QUERIES, VERIFIED  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def _rewrite_safe_divide(s: str) -> str:
    """SAFE_DIVIDE(a, b) -> (a / NULLIF(b, 0)), handling nested parentheses."""
    key = "SAFE_DIVIDE("
    while key in s:
        i = s.index(key)
        j = i + len(key)
        depth, comma = 1, None
        k = j
        while depth:
            ch = s[k]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 1 and comma is None:
                comma = k
            k += 1
        a, b = s[j:comma].strip(), s[comma + 1:k - 1].strip()
        s = s[:i] + f"({a} / NULLIF({b}, 0))" + s[k:]
    return s


def to_duckdb(sql: str) -> str:
    s = re.sub(r"`cymbal_voyages\.(\w+)`", r"\1", sql)
    s = re.sub(r"COUNTIF\(", "COUNT_IF(", s)
    s = _rewrite_safe_divide(s)
    s = re.sub(r"DATE_TRUNC\(([\w.]+),\s*MONTH\)", r"CAST(DATE_TRUNC('month', \1) AS DATE)", s)
    s = re.sub(r"DATE_TRUNC\(([\w.]+),\s*WEEK\(MONDAY\)\)", r"CAST(DATE_TRUNC('week', \1) AS DATE)", s)
    s = re.sub(r"\bIF\(", "IF(", s)  # DuckDB supports IF(cond, a, b)
    return s


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for folder in sorted(OUT.iterdir()):
        if folder.is_dir():
            con.execute(f"CREATE VIEW {folder.name} AS SELECT * FROM read_parquet('{folder}/*.parquet')")
    return con


def md_table(cols, rows) -> str:
    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:,.0f}"
        if isinstance(v, int):
            return f"{v:,}"
        return str(v)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join([" --- "] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def run_all(con) -> dict:
    results = {}
    for key, title, sql in QUERIES:
        cur = con.execute(to_duckdb(sql))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        results[key] = (title, sql.strip(), cols, rows)
    for i, (title, sql, _required) in enumerate(VERIFIED):
        cur = con.execute(to_duckdb(sql))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        results[f"verified_{i+1}"] = (title, sql.strip(), cols, rows)
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="render docs/anomaly-walkthrough.md")
    ap.add_argument("--only", help="run one query key")
    args = ap.parse_args()
    con = connect()
    results = run_all(con)
    if args.write:
        from build_walkthrough import render  # noqa: WPS433
        text = render(results)
        (ROOT / "docs" / "anomaly-walkthrough.md").write_text(text, encoding="utf-8")
        print(f"wrote docs/anomaly-walkthrough.md ({len(text):,} chars)")
        return 0
    for key, (title, sql, cols, rows) in results.items():
        if args.only and key != args.only:
            continue
        print(f"\n### {key} — {title}\n")
        print(md_table(cols, rows[:60]))
        if len(rows) > 60:
            print(f"... {len(rows) - 60} more rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
