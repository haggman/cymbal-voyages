#!/usr/bin/env bash
# Build and publish the two lab service images to a PUBLIC Artifact Registry repo.
# Run once per release, in Cloud Shell, from the repo root, in the project that owns the images:
#
#   bash services/scripts/build_images.sh            # uses the current gcloud project
#   IMAGE_PROJECT=other-project bash services/scripts/build_images.sh
#
# Optional: TOOLBOX_VERSION=<tag> to pin a specific MCP Toolbox release (default: the release
# that Google's :latest currently points to, resolved to its version tag; never :latest itself).
# ORCH_TAG=<tag> for the orchestrator image (default 1.0.0).
set -euo pipefail
IMAGE_PROJECT="${IMAGE_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
[[ -n "$IMAGE_PROJECT" ]] || { echo "No project: run gcloud config set project <id> or set IMAGE_PROJECT" >&2; exit 1; }
echo "Publishing images to project: $IMAGE_PROJECT"
REGION="${REGION:-us-central1}"
REPO="${REPO:-cymbal-voyages}"
ORCH_TAG="${ORCH_TAG:-1.0.0}"
GOOGLE_TOOLBOX="us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox"
REG="${REGION}-docker.pkg.dev/${IMAGE_PROJECT}/${REPO}"

gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com compute.googleapis.com --project "$IMAGE_PROJECT"

# Cloud Build runs as the Compute Engine default service account in newer projects. It only
# exists once the Compute API is on, and it needs to write logs and push images; the person
# running this script needs to be allowed to act as it.
PN=$(gcloud projects describe "$IMAGE_PROJECT" --format='value(projectNumber)')
BUILD_SA="${PN}-compute@developer.gserviceaccount.com"
for i in 1 2 3 4 5 6; do
  gcloud iam service-accounts describe "$BUILD_SA" --project "$IMAGE_PROJECT" >/dev/null 2>&1 && break
  echo "Waiting for $BUILD_SA to appear..."; sleep 10
done
for r in roles/logging.logWriter roles/artifactregistry.writer roles/storage.objectViewer; do
  gcloud projects add-iam-policy-binding "$IMAGE_PROJECT" --member="serviceAccount:${BUILD_SA}" --role="$r" --condition=None >/dev/null
done
gcloud iam service-accounts add-iam-policy-binding "$BUILD_SA" --project "$IMAGE_PROJECT" \
  --member="user:$(gcloud config get-value account 2>/dev/null)" --role=roles/iam.serviceAccountUser >/dev/null
if ! gcloud artifacts repositories describe "$REPO" --location "$REGION" --project "$IMAGE_PROJECT" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location "$REGION" \
    --description="Cymbal Voyages lab service images (mkt016), public read" --project "$IMAGE_PROJECT"
fi
# Public read, so any lab project can pull without a grant.
gcloud artifacts repositories add-iam-policy-binding "$REPO" --location "$REGION" --project "$IMAGE_PROJECT" \
  --member=allUsers --role=roles/artifactregistry.reader >/dev/null

# 1. MCP Toolbox for Databases: mirror Google's image at a pinned version.
if [[ -z "${TOOLBOX_VERSION:-}" ]]; then
  # The newest release tag (e.g. 1.2.3 or v1.2.3), never "latest".
  TOOLBOX_VERSION=$(gcloud artifacts docker tags list "$GOOGLE_TOOLBOX" --format='value(tag.basename())' 2>/dev/null \
    | python3 -c 'import sys,re
t=[l.strip() for l in sys.stdin if re.fullmatch(r"v?\d+\.\d+\.\d+", l.strip())]
t.sort(key=lambda v:[int(x) for x in re.findall(r"\d+",v)])
print(t[-1] if t else "")' || true)
fi
[[ -n "$TOOLBOX_VERSION" && "$TOOLBOX_VERSION" != "latest" ]] || { echo "Could not resolve a Toolbox version tag. Tags seen:" >&2; gcloud artifacts docker tags list "$GOOGLE_TOOLBOX" --format="value(tag.basename())" 2>&1 | head -20 >&2; exit 1; }
echo "Toolbox version: $TOOLBOX_VERSION"
# Mirror with Cloud Build (no local Docker needed): a one-line Dockerfile FROM the pinned image.
MIRROR_DIR=$(mktemp -d)
echo "FROM ${GOOGLE_TOOLBOX}:${TOOLBOX_VERSION}" > "$MIRROR_DIR/Dockerfile"
gcloud builds submit "$MIRROR_DIR" --project "$IMAGE_PROJECT" --region "$REGION" \
  --tag "${REG}/toolbox:${TOOLBOX_VERSION}"
rm -rf "$MIRROR_DIR"

# 2. The ADK orchestrator (A2A server).
gcloud builds submit agents/orchestrator --project "$IMAGE_PROJECT" --region "$REGION" \
  --tag "${REG}/orchestrator:${ORCH_TAG}"

echo
echo "Published:"
echo "  ${REG}/toolbox:${TOOLBOX_VERSION}"
echo "  ${REG}/orchestrator:${ORCH_TAG}"
echo "Record both in docs/services.md."
