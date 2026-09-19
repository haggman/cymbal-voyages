#!/usr/bin/env bash
# Deploy the lab services into a lab project from the prebuilt public images.
# This is what provisioning (Start Lab) does; run it in Cloud Shell from the repo root:
#
#   bash services/scripts/deploy_services.sh
#
# The image repo defaults to the published one below; the Toolbox and orchestrator tags are
# read live from that repo (the newest of each). Override with IMAGE_REPO, TOOLBOX_VERSION, ORCH_TAG.
#
# Needs: the cymbal_voyages dataset already loaded in this project.
set -euo pipefail
PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
IMAGE_PROJECT="${IMAGE_PROJECT:-__IMAGE_PROJECT__}"
IMAGE_REPO="${IMAGE_REPO:-us-central1-docker.pkg.dev/${IMAGE_PROJECT}/cymbal-voyages}"
newest_tag() {  # newest version tag of an image in the public repo
  gcloud artifacts docker tags list "${IMAGE_REPO}/$1" --format='value(tag.basename())' 2>/dev/null \
    | grep -v '^latest$' \
    | python3 -c 'import sys,re; t=[l.strip() for l in sys.stdin if l.strip()]; t.sort(key=lambda v:[int(x) for x in re.findall(r"\d+",v)]); print(t[-1] if t else "")'
}
TOOLBOX_VERSION="${TOOLBOX_VERSION:-$(newest_tag toolbox)}"
ORCH_TAG="${ORCH_TAG:-$(newest_tag orchestrator)}"
[[ -n "$TOOLBOX_VERSION" && -n "$ORCH_TAG" ]] || { echo "Could not read image tags from ${IMAGE_REPO}; has build_images.sh been run?" >&2; exit 1; }
echo "Images: ${IMAGE_REPO}/toolbox:${TOOLBOX_VERSION}  ${IMAGE_REPO}/orchestrator:${ORCH_TAG}"
ORCH_MODEL="${ORCH_MODEL:-gemini-3.5-flash}"
TOOLBOX_SVC="${TOOLBOX_SVC:-audience-tools}"
ORCH_SVC="${ORCH_SVC:-orchestrator}"
SECRET="${SECRET:-audience-tools-config}"
PN=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
TOOLBOX_SA="audience-tools-sa@${PROJECT}.iam.gserviceaccount.com"
ORCH_SA="orchestrator-sa@${PROJECT}.iam.gserviceaccount.com"
GE_AGENT="service-${PN}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

gcloud services enable run.googleapis.com secretmanager.googleapis.com bigquery.googleapis.com \
  aiplatform.googleapis.com discoveryengine.googleapis.com --project "$PROJECT"
gcloud beta services identity create --service=discoveryengine.googleapis.com --project "$PROJECT" >/dev/null

# Service accounts and roles.
for sa in audience-tools-sa orchestrator-sa; do
  gcloud iam service-accounts describe "${sa}@${PROJECT}.iam.gserviceaccount.com" --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud iam service-accounts create "$sa" --project "$PROJECT"
done
grant() { gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$1" --role="$2" --condition=None >/dev/null; }
for r in roles/bigquery.jobUser roles/bigquery.dataViewer roles/bigquery.dataEditor roles/secretmanager.secretAccessor roles/aiplatform.user; do
  grant "$TOOLBOX_SA" "$r"; done
for r in roles/bigquery.jobUser roles/bigquery.dataViewer roles/aiplatform.user; do
  grant "$ORCH_SA" "$r"; done

# tools.yaml as a secret (new version each run).
if gcloud secrets describe "$SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud secrets versions add "$SECRET" --data-file="$HERE/services/toolbox/tools.yaml" --project "$PROJECT"
else
  gcloud secrets create "$SECRET" --data-file="$HERE/services/toolbox/tools.yaml" --project "$PROJECT"
fi

# Audience Tools (MCP Toolbox for Databases).
gcloud run deploy "$TOOLBOX_SVC" --project "$PROJECT" --region "$REGION" \
  --image "${IMAGE_REPO}/toolbox:${TOOLBOX_VERSION}" \
  --service-account "$TOOLBOX_SA" --no-allow-unauthenticated --min-instances=1 \
  --set-secrets "/secrets/tools.yaml=${SECRET}:latest" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT}" \
  --args="--tools-file=/secrets/tools.yaml,--address=0.0.0.0,--port=8080"

# Orchestrator (ADK, A2A). The URL is deterministic, so the card can be written before deploy.
ORCH_URL="https://${ORCH_SVC}-${PN}.${REGION}.run.app"
gcloud run deploy "$ORCH_SVC" --project "$PROJECT" --region "$REGION" \
  --image "${IMAGE_REPO}/orchestrator:${ORCH_TAG}" \
  --service-account "$ORCH_SA" --no-allow-unauthenticated --min-instances=1 --memory 1Gi \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_VERTEXAI=TRUE,BQ_PROJECT=${PROJECT},BQ_DATASET=cymbal_voyages,ORCHESTRATOR_MODEL=${ORCH_MODEL},AGENT_URL=${ORCH_URL}"

# Gemini Enterprise calls both services with a Google-signed ID token as its service agent.
for svc in "$TOOLBOX_SVC" "$ORCH_SVC"; do
  gcloud run services add-iam-policy-binding "$svc" --project "$PROJECT" --region "$REGION" \
    --member="serviceAccount:${GE_AGENT}" --role=roles/run.invoker >/dev/null
done

# The trimmed agent card students paste into Gemini Enterprise.
sed "s#__AGENT_URL__#${ORCH_URL}#g" "$HERE/agents/orchestrator/orchestrator/agent.card.template.json" > "$HERE/orchestrator-card.json"

TOOLBOX_URL=$(gcloud run services describe "$TOOLBOX_SVC" --project "$PROJECT" --region "$REGION" --format='value(status.url)')
echo
echo "Audience Tools MCP URL : ${TOOLBOX_URL}/mcp"
echo "Orchestrator URL       : ${ORCH_URL}   (card: ${ORCH_URL}/a2a/orchestrator/.well-known/agent-card.json)"
echo "Card to paste          : $HERE/orchestrator-card.json"
