#!/usr/bin/env bash
# From nothing to out/ + schemas/ + docs/ in one command (same as `make`).
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
python3 generate_warehouse.py
python3 sql/verify_local.py --write
python3 sql/build_dictionary.py
echo "Parquet in out/, BigQuery schemas in schemas/, docs in docs/."
