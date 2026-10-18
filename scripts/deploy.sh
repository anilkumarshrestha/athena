#!/usr/bin/env bash
# Deploy Athena to Cloud Run (one service: API + WebSocket + frontend).
#   ./scripts/deploy.sh            # first deploy and every redeploy
# Optional: GOOGLE_OAUTH_CLIENT_ID=<web client id> for "Sign in with Google" (public, not a secret).
# Needs: gcloud logged in, project set, billing on. Creates (idempotent): Secret Manager secret
# for the Gemini key, a private media bucket, a service account with least privilege.
set -euo pipefail

PROJECT="$(gcloud config get-value project 2>/dev/null)"
REGION="${REGION:-asia-south1}"   # Mumbai: closest Cloud Run region to Nepal
MIN_INSTANCES="${MIN_INSTANCES:-0}"  # 0: scale to zero (cheap); MIN_INSTANCES=1 on demo days (no cold start)
SERVICE="athena"
BUCKET="athena-media-${PROJECT}"
SA="athena-run@${PROJECT}.iam.gserviceaccount.com"
cd "$(dirname "$0")/.."

echo "project=$PROJECT region=$REGION"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com speech.googleapis.com aiplatform.googleapis.com storage.googleapis.com \
  firestore.googleapis.com --quiet

# 1. Gemini key -> Secret Manager. Parsed the way the app parses .env (inline comments stripped);
#    never printed, never in the image.
gcloud secrets describe gemini-api-key >/dev/null 2>&1 || gcloud secrets create gemini-api-key --replication-policy=automatic
.venv/bin/python -c 'from athena.config import settings; print(settings().gemini_api_key, end="")' \
  | gcloud secrets versions add gemini-api-key --data-file=- >/dev/null

# 1b. Family cookie signing key (athena/family.py): created once, random, never printed.
#     Kept across deploys so families stay signed in.
if ! gcloud secrets describe family-secret >/dev/null 2>&1; then
  gcloud secrets create family-secret --replication-policy=automatic
  python3 -c 'import secrets; print(secrets.token_hex(32), end="")' | gcloud secrets versions add family-secret --data-file=- >/dev/null
fi

# 2. Private bucket for story illustrations (served through the API only). Word audio and
#    word pictures stay in the instance cache, warm-started from the image.
gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1 || \
  gcloud storage buckets create "gs://${BUCKET}" --location="$REGION" --uniform-bucket-level-access --public-access-prevention

# 3. Service account: read the secret, use the bucket, call Speech-to-Text, read/write Firestore.
gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 || \
  gcloud iam service-accounts create athena-run --display-name="Athena Cloud Run"
gcloud secrets add-iam-policy-binding gemini-api-key --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor --quiet >/dev/null
gcloud secrets add-iam-policy-binding family-secret --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor --quiet >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --member="serviceAccount:$SA" --role=roles/storage.objectAdmin --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role=roles/speech.client --condition=None --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role=roles/datastore.user --condition=None --quiet >/dev/null

# "Sign in with Google": the public Web client id, from the shell or else from .env.
GOOGLE_OAUTH_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID:-$(.venv/bin/python -c 'from athena.config import settings; print(settings().google_oauth_client_id, end="")')}"

# 4. Build from source with Cloud Build and deploy.
#    Learners + story history in Firestore: they survive restarts and scale-to-zero.
#    Max one instance: an open story and its prepared "next" live in that instance's memory.
#    Long timeout + session affinity: WebSocket live follow-along.
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --service-account "$SA" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,FAMILY_SECRET=family-secret:latest" \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${PROJECT},MEDIA_BUCKET=${BUCKET},STORE_BACKEND=firestore,GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID:-}" \
  --min-instances "$MIN_INSTANCES" --max-instances 1 \
  --cpu 2 --memory 2Gi --timeout 900 --session-affinity \
  --allow-unauthenticated \
  --quiet

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "deployed: $URL"
curl -sf "$URL/api/health" && echo " health ok"
