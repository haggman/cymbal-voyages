#!/usr/bin/env python3
"""
Embed every destination and package description with Vertex AI gemini-embedding-001 (3,072 dims)
and write out/catalog_embeddings/part-000.parquet in the BigQuery-ready layout.

    pip install -r embeddings/requirements.txt
    PROJECT_ID=my-project python3 embeddings/build_embeddings.py
    PROJECT_ID=my-project LOCATION=us-central1 python3 embeddings/build_embeddings.py --workers 4

Same model, dimension and SDK pattern as the mkt013 CymbalGoal lab (google-genai with
vertexai=True; gemini-embedding-001 on Vertex accepts one text per request). 360 texts take about
a minute. Re-running overwrites the output; --resume keeps vectors already written.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cvgen import writer  # noqa: E402

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 3072
TASK_TYPE = "RETRIEVAL_DOCUMENT"
MAX_RETRIES = 6


def project_id() -> str:
    pid = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not pid:
        pid = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True).stdout.strip()
    if not pid or pid == "(unset)":
        raise SystemExit("Set PROJECT_ID (or gcloud config set project ...)")
    return pid


def catalog_items() -> pd.DataFrame:
    dest = pd.read_parquet(ROOT / "out" / "destinations")
    pkg = pd.read_parquet(ROOT / "out" / "packages").merge(dest[["destination_id", "category", "name"]].rename(columns={"name": "destination_name"}), on="destination_id")
    d = pd.DataFrame({
        "item_type": "destination", "item_id": dest["destination_id"], "name": dest["name"], "category": dest["category"],
        "content": dest["name"] + ". " + dest["region"] + ", " + dest["country"] + ". Category: " + dest["category"].str.replace("_", " ") + ". " + dest["description"],
    })
    p = pd.DataFrame({
        "item_type": "package", "item_id": pkg["package_id"], "name": pkg["name"], "category": pkg["category"],
        "content": pkg["name"] + ". " + pkg["nights"].astype(str) + " nights in " + pkg["destination_name"] + ". Category: " + pkg["category"].str.replace("_", " ") + ". " + pkg["description"],
    })
    return pd.concat([d, p], ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--location", default=os.environ.get("LOCATION", "us-central1"))
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    from google import genai
    from google.genai import types as gtypes

    client = genai.Client(vertexai=True, project=project_id(), location=args.location)
    items = catalog_items()
    out_dir = ROOT / "out" / "catalog_embeddings"
    done: dict[str, list[float]] = {}
    if args.resume and out_dir.exists():
        prev = pd.read_parquet(out_dir)
        done = {k: list(v) for k, v in zip(prev["item_id"], prev["embedding"])}
        print(f"resume: {len(done)} vectors already present")

    def embed(item_id: str, text: str) -> tuple[str, list[float]]:
        cfg = gtypes.EmbedContentConfig(output_dimensionality=EMBED_DIM, task_type=TASK_TYPE)
        last = None
        for attempt in range(MAX_RETRIES):
            try:
                r = client.models.embed_content(model=EMBED_MODEL, contents=text, config=cfg)
                vec = list(r.embeddings[0].values)
                if len(vec) != EMBED_DIM:
                    raise RuntimeError(f"got {len(vec)} dims, expected {EMBED_DIM}")
                return item_id, vec
            except Exception as exc:  # noqa: BLE001
                last = exc
                time.sleep(min(30, 2 ** attempt) + np.random.uniform(0, 1))
        raise RuntimeError(f"{item_id}: {last}")

    todo = [(i, t) for i, t in zip(items["item_id"], items["content"]) if i not in done]
    print(f"embedding {len(todo)} of {len(items)} texts with {EMBED_MODEL} @ {EMBED_DIM}d in {args.location}")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(embed, i, t) for i, t in todo]
        for n, f in enumerate(as_completed(futures), 1):
            item_id, vec = f.result()
            done[item_id] = vec
            if n % 50 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)}  {time.time() - t0:.0f}s")

    items["embedding"] = [np.round(np.array(done[i], dtype=np.float64), 6).tolist() for i in items["item_id"]]
    items["model"] = EMBED_MODEL
    items["dimensions"] = EMBED_DIM
    paths = writer.write_table(items, "catalog_embeddings", ROOT / "out")
    print(f"wrote {paths[0]} ({len(items)} rows, {paths[0].stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
