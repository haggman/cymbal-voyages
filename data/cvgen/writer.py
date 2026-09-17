"""Typed Parquet output. Every table is a folder out/<table>/part-NNN.parquet so bq load can glob it."""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .schemas import SCHEMAS

ROWS_PER_PART = 150_000

_TYPES = {"STRING": pa.string(), "INT64": pa.int64(), "FLOAT64": pa.float64(), "BOOL": pa.bool_(),
          "DATE": pa.date32(), "TIMESTAMP": pa.timestamp("us")}


def arrow_schema(table: str) -> pa.Schema:
    fields = []
    for name, typ, mode, desc in SCHEMAS[table]["columns"]:
        t = _TYPES[typ]
        if mode == "REPEATED":
            t = pa.list_(t)
        fields.append(pa.field(name, t, nullable=(mode != "REQUIRED"), metadata={"description": desc}))
    return pa.schema(fields)


def write_table(df: pd.DataFrame, table: str, out_dir: Path) -> list[Path]:
    schema = arrow_schema(table)
    cols = [f.name for f in schema]
    missing = [c for c in cols if c not in df.columns]
    assert not missing, f"{table}: missing columns {missing}"
    df = df[cols].reset_index(drop=True)
    folder = out_dir / table
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    paths = []
    n = max(1, len(df))
    for i, start in enumerate(range(0, n, ROWS_PER_PART)):
        chunk = df.iloc[start:start + ROWS_PER_PART]
        tbl = pa.Table.from_pandas(chunk, schema=schema, preserve_index=False)
        p = folder / f"part-{i:03d}.parquet"
        pq.write_table(tbl, p, compression="snappy")
        paths.append(p)
    return paths
