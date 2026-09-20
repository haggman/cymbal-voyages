#!/usr/bin/env bash
# Keep the Start Lab Terraform in step with the repo files it embeds, then mirror
# the tree into the lab folder Qwiklabs actually runs (startup_script path:
# terraform, relative to the lab folder in gcp-ce-content).
#
#   bash provisioning/sync.sh            # copy sources -> files/, mirror to the lab folder
#   bash provisioning/sync.sh --check    # exit 1 if anything is out of step (no writes)
#
# Why copies: the Qwiklabs runner only sees the lab folder, not this repo, so
# file() can only read what sits beside main.tf. The canonical sources stay where
# they are; files/ is generated. Never edit files/ by hand.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
TF="$HERE/terraform"
LAB_DIR="${LAB_DIR:-$REPO/../../gcp-ce-content/labs/mkt016-from-question-to-campaign}"
CHECK=0; [[ "${1:-}" == "--check" ]] && CHECK=1

# name:source pairs (plain list, not an associative array: macOS ships bash 3.2)
SRC=(
  "tools.yaml:services/toolbox/tools.yaml"
  "agent.card.template.json:agents/orchestrator/orchestrator/agent.card.template.json"
  "train_propensity.sql:data/sql/train_propensity.sql"
)
stale=0
mkdir -p "$TF/files"
for pair in "${SRC[@]}"; do
  f="${pair%%:*}"; src="${pair#*:}"
  if ! cmp -s "$REPO/$src" "$TF/files/$f"; then
    stale=1
    if (( CHECK )); then echo "STALE  files/$f  (source: $src)"; else cp "$REPO/$src" "$TF/files/$f"; echo "copied files/$f"; fi
  fi
done

# Image pins: the Terraform must point at tags that actually exist in the public repo,
# and it should not silently lag behind a newer build. Skipped when gcloud is absent.
# (Sep 20: the orchestrator pin sat at 1.0.0 for a whole test run after 1.0.1 was published.)
REPO_IMG="us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages"
if command -v gcloud >/dev/null; then
  for img in toolbox orchestrator; do
    pin=$(sed -n "/variable \"${img}_tag\"/,/}/p" "$TF/variables.tf" | sed -n 's/.*default *= *"\(.*\)".*/\1/p')
    [[ -n "$pin" ]] || continue
    tags=$(gcloud artifacts docker tags list "$REPO_IMG/$img" --format='value(tag.basename())' 2>/dev/null | grep -v '^latest$')
    if [[ -z "$tags" ]]; then echo "NOTE   could not read tags for $img (no access to $REPO_IMG?)"; continue; fi
    if ! grep -qx "$pin" <<<"$tags"; then echo "STALE  $img: Terraform pins $pin, which is NOT published"; stale=1; fi
    newest=$(sort -V <<<"$tags" | tail -1)
    if [[ "$newest" != "$pin" ]]; then echo "NOTE   $img: newest published is $newest, Terraform pins $pin (deliberate?)"; fi
  done
fi

if [[ -d "$LAB_DIR" ]]; then
  if (( CHECK )); then
    diff -rq --exclude='.terraform*' --exclude='*.tfstate*' "$TF" "$LAB_DIR/terraform" >/dev/null 2>&1 || { echo "STALE  lab folder terraform/"; stale=1; }
  else
    mkdir -p "$LAB_DIR/terraform/files"
    for p in runtime.yaml versions.tf provider.tf variables.tf main.tf outputs.tf; do cp "$TF/$p" "$LAB_DIR/terraform/$p"; done
    cp "$TF"/files/* "$LAB_DIR/terraform/files/"
    echo "mirrored terraform/ -> $LAB_DIR/terraform"
  fi
else
  echo "lab folder not found at $LAB_DIR (set LAB_DIR); skipped the mirror" >&2
fi
(( CHECK )) && { (( stale )) && exit 1 || echo "in step"; }
exit 0
