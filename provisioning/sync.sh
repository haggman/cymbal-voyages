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

declare -A SRC=(
  [tools.yaml]="services/toolbox/tools.yaml"
  [agent.card.template.json]="agents/orchestrator/orchestrator/agent.card.template.json"
  [train_propensity.sql]="data/sql/train_propensity.sql"
)
stale=0
mkdir -p "$TF/files"
for f in "${!SRC[@]}"; do
  if ! cmp -s "$REPO/${SRC[$f]}" "$TF/files/$f"; then
    stale=1
    if (( CHECK )); then echo "STALE  files/$f  (source: ${SRC[$f]})"; else cp "$REPO/${SRC[$f]}" "$TF/files/$f"; echo "copied files/$f"; fi
  fi
done

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
