#!/usr/bin/env bash
# One command, run from the repo root on a machine with gcloud: build + publish the images,
# deploy into the lab project, and run the end-to-end test. Everything is logged to
# .runlogs/ in the repo so the build conversation can read it.
#
#   IMAGE_PROJECT=<your project>  IMAGE_ACCOUNT=<you@...> \
#   LAB_PROJECT=<qwiklabs project> LAB_ACCOUNT=<student-...@qwiklabs.net> \
#   bash services/scripts/run_phase2_check.sh
#
# Both accounts must already be signed in (gcloud auth login <account>). Set SKIP_BUILD=1 to
# reuse published images (then also set TOOLBOX_VERSION).
set -uo pipefail
cd "$(dirname "$0")/../.."
mkdir -p .runlogs
STAMP=$(date +%Y%m%d-%H%M%S)
LOG=".runlogs/phase2-${STAMP}.log"
: "${IMAGE_PROJECT:?}" "${LAB_PROJECT:?}"
REGION="${REGION:-us-central1}"
exec > >(tee "$LOG") 2>&1
echo "run ${STAMP}  image=${IMAGE_PROJECT} (${IMAGE_ACCOUNT:-active})  lab=${LAB_PROJECT} (${LAB_ACCOUNT:-active})"

if [[ -z "${SKIP_BUILD:-}" ]]; then
  echo "=== BUILD ==="; SECONDS=0
  CLOUDSDK_CORE_ACCOUNT="${IMAGE_ACCOUNT:-}" IMAGE_PROJECT="$IMAGE_PROJECT" \
    bash services/scripts/build_images.sh | tee .runlogs/build-out.txt || { echo "BUILD FAILED"; exit 1; }
  echo "build took ${SECONDS}s"
  TOOLBOX_VERSION=$(sed -n 's#.*/toolbox:\(.*\)$#\1#p' .runlogs/build-out.txt | tail -1)
fi
: "${TOOLBOX_VERSION:?}"
export CLOUDSDK_CORE_ACCOUNT="${LAB_ACCOUNT:-}" CLOUDSDK_CORE_PROJECT="$LAB_PROJECT"
echo "=== DEPLOY (toolbox ${TOOLBOX_VERSION}) ==="; SECONDS=0
PROJECT="$LAB_PROJECT" IMAGE_REPO="${REGION}-docker.pkg.dev/${IMAGE_PROJECT}/cymbal-voyages" \
  TOOLBOX_VERSION="$TOOLBOX_VERSION" bash services/scripts/deploy_services.sh || { echo "DEPLOY FAILED"; exit 1; }
echo "deploy took ${SECONDS}s"
echo "=== TEST ==="
PROJECT="$LAB_PROJECT" bash services/scripts/test_services.sh
echo "=== DONE: $LOG ==="
