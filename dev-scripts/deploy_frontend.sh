#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

TF_DIR="infra/environments/dev"

API_BASE_URL=$(cd "$TF_DIR" && terraform output -raw dashboard_api_endpoint)
API_BASE_URL="${API_BASE_URL%/}"
WRITE_API_KEY=$(cd "$TF_DIR" && terraform output -raw dashboard_write_api_key)
BUCKET=$(cd "$TF_DIR" && terraform output -raw dashboard_bucket_name)
DISTRIBUTION_ID=$(cd "$TF_DIR" && terraform output -raw dashboard_distribution_id)

echo "API: $API_BASE_URL"
echo "Bucket: $BUCKET"
echo "Distribution: $DISTRIBUTION_ID"

cd frontend
cat > .env.production <<EOF
VITE_API_BASE_URL=${API_BASE_URL}
VITE_WRITE_API_KEY=${WRITE_API_KEY}
EOF

npm install
npm run build

aws s3 sync dist/ "s3://${BUCKET}/" --delete

aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths "/*"

echo "Deployed. Dashboard URL:"
cd ../"$TF_DIR" && terraform output -raw dashboard_url && echo
