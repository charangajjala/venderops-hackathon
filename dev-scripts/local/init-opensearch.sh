#!/bin/sh
set -eu

OS_URL="${OPENSEARCH_URL:-http://opensearch:9200}"
OSD_URL="${OPENSEARCH_DASHBOARDS_URL:-http://opensearch-dashboards:5601}"
TEMPLATE_DIR="${TEMPLATE_DIR:-/templates}"
DASHBOARDS_DIR="${DASHBOARDS_DIR:-/dashboards}"
WORKSPACE_NAME="${WORKSPACE_NAME:-VendorOps Observability}"
DATASOURCE_ID="${DATASOURCE_ID:-vendorops-local}"

osd() {
  method="$1"
  path="$2"
  data_file="${3:-}"
  if [ -n "$data_file" ]; then
    curl -sS -X "$method" "${OSD_URL}${path}" \
      -H "osd-xsrf: true" \
      -H "Content-Type: application/json" \
      --data-binary "@${data_file}"
  else
    curl -sS -X "$method" "${OSD_URL}${path}" \
      -H "osd-xsrf: true" \
      -H "Content-Type: application/json"
  fi
}

osd_body() {
  method="$1"
  path="$2"
  body="$3"
  curl -sS -X "$method" "${OSD_URL}${path}" \
    -H "osd-xsrf: true" \
    -H "Content-Type: application/json" \
    -d "${body}"
}

wait_for() {
  name="$1"
  url="$2"
  echo "Waiting for ${name} at ${url} ..."
  i=0
  while [ "$i" -lt 90 ]; do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "${name} is up."
      return 0
    fi
    i=$((i + 1))
    sleep 3
  done
  echo "Timed out waiting for ${name}" >&2
  return 1
}

wait_for_dashboards_healthy() {
  echo "Waiting for OpenSearch Dashboards to become healthy..."
  i=0
  while [ "$i" -lt 60 ]; do
    body="$(curl -sf "${OSD_URL}/api/status" || true)"
    if echo "${body}" | grep -q '"state":"green"'; then
      echo "OpenSearch Dashboards is healthy."
      return 0
    fi
    if echo "${body}" | grep -q '"level":"available"'; then
      echo "OpenSearch Dashboards is available."
      return 0
    fi
    i=$((i + 1))
    sleep 5
  done
  echo "Timed out waiting for Dashboards health" >&2
  echo "${body:-no status body}" >&2
  return 1
}

extract_result_id() {
  echo "$1" | tr -d '\n' | sed 's/[[:space:]]//g' | sed -n 's/.*"result":{"id":"\([^"]*\)".*/\1/p'
}

find_workspace_id() {
  list="$(osd_body POST /api/workspaces/_list '{"perPage":100}')"
  echo "${list}" | tr '}' '\n' | grep -F "\"name\":\"${WORKSPACE_NAME}\"" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -n 1
}

wait_for "OpenSearch" "${OS_URL}/_cluster/health"
wait_for_dashboards_healthy

echo "Waiting for Dashboards workspace API..."
i=0
while [ "$i" -lt 40 ]; do
  if curl -sf -X POST "${OSD_URL}/api/workspaces/_list" \
    -H "osd-xsrf: true" \
    -H "Content-Type: application/json" \
    -d '{}' >/dev/null 2>&1; then
    echo "Workspace API is ready."
    break
  fi
  i=$((i + 1))
  sleep 3
done

echo "Installing index templates..."
curl -sf -X PUT "${OS_URL}/_index_template/docker-logs" \
  -H "Content-Type: application/json" \
  --data-binary "@${TEMPLATE_DIR}/docker-logs.json"

curl -sf -X PUT "${OS_URL}/_template/otel-v1-apm-span-index-template" \
  -H "Content-Type: application/json" \
  --data-binary "@${TEMPLATE_DIR}/otel-v1-apm-span.json"

echo "Creating bootstrap indices..."
curl -sS -X PUT "${OS_URL}/docker-logs" \
  -H "Content-Type: application/json" \
  -d '{"aliases":{"docker-logs-alias":{}}}' >/dev/null || true

curl -sS -X PUT "${OS_URL}/otel-v1-apm-service-map" \
  -H "Content-Type: application/json" \
  -d '{"settings":{"number_of_shards":1,"number_of_replicas":0}}' >/dev/null || true

echo "Creating Dashboards data source ${DATASOURCE_ID}..."
DS_RESP="$(osd POST "/api/saved_objects/data-source/${DATASOURCE_ID}?overwrite=true" "${DASHBOARDS_DIR}/data-source.json")"
echo "${DS_RESP}"

echo "Creating or finding observability workspace..."
WORKSPACE_ID="$(find_workspace_id || true)"
if [ -z "${WORKSPACE_ID}" ]; then
  CREATE_WS="$(osd POST /api/workspaces "${DASHBOARDS_DIR}/workspace.json" || true)"
  echo "${CREATE_WS}"
  WORKSPACE_ID="$(extract_result_id "${CREATE_WS}")"
fi
if [ -z "${WORKSPACE_ID}" ]; then
  WORKSPACE_ID="$(find_workspace_id || true)"
fi
if [ -z "${WORKSPACE_ID}" ]; then
  echo "Failed to create or find workspace '${WORKSPACE_NAME}'" >&2
  exit 1
fi
echo "Using workspace id ${WORKSPACE_ID}"

wait_for_docs() {
  index="$1"
  echo "Waiting for documents in ${index}..."
  i=0
  while [ "$i" -lt 40 ]; do
    count="$(curl -sf "${OS_URL}/${index}/_count" | sed -n 's/.*"count":\([0-9]*\).*/\1/p' || true)"
    if [ -n "${count}" ] && [ "${count}" -gt 0 ] 2>/dev/null; then
      echo "${index} has ${count} documents."
      return 0
    fi
    i=$((i + 1))
    sleep 3
  done
  echo "Timed out waiting for documents in ${index}; continuing with seeded dataset fields."
}

write_datasets() {
  echo "Writing datasets in workspace ${WORKSPACE_ID}..."
  osd POST "/w/${WORKSPACE_ID}/api/saved_objects/index-pattern/docker-logs?overwrite=true" \
    "${DASHBOARDS_DIR}/dataset-docker-logs.json"
  echo
  osd POST "/w/${WORKSPACE_ID}/api/saved_objects/index-pattern/otel-v1-apm-span?overwrite=true" \
    "${DASHBOARDS_DIR}/dataset-otel-traces.json"
  echo
}

write_datasets

echo "Associating data source and datasets with workspace..."
osd_body POST /api/workspaces/_associate "{
  \"workspaceId\": \"${WORKSPACE_ID}\",
  \"savedObjects\": [
    {\"type\": \"data-source\", \"id\": \"${DATASOURCE_ID}\"},
    {\"type\": \"index-pattern\", \"id\": \"docker-logs\"},
    {\"type\": \"index-pattern\", \"id\": \"otel-v1-apm-span\"}
  ]
}"
echo

echo "Creating traces-logs correlation..."
osd POST "/w/${WORKSPACE_ID}/api/saved_objects/correlations/traces-logs-correlation?overwrite=true" \
  "${DASHBOARDS_DIR}/correlation-traces-logs.json" || true
echo

echo "Associating correlation with workspace..."
osd_body POST /api/workspaces/_associate "{
  \"workspaceId\": \"${WORKSPACE_ID}\",
  \"savedObjects\": [
    {\"type\": \"correlations\", \"id\": \"traces-logs-correlation\"}
  ]
}" || true
echo

echo "Setting default workspace..."
osd_body POST /api/opensearch-dashboards/settings \
  "{\"changes\":{\"defaultWorkspace\":\"${WORKSPACE_ID}\"}}" || true
echo

# Dashboards captures index-pattern fields asynchronously. If the index is still
# empty, it overwrites seeded time fields and Discover/Explore show no data.
wait_for_docs "docker-logs"
wait_for_docs "otel-v1-apm-span*"
sleep 5
write_datasets

echo "OpenSearch Dashboards bootstrap complete."
echo "Workspace: ${OSD_URL}/w/${WORKSPACE_ID}"
echo "Datasets: Docker logs (logs), OTel traces (traces)"
