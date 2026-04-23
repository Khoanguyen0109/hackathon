#!/usr/bin/env bash
# End-to-end client walkthrough — mirrors the 5 screens of the user flow.
#
# Prereq: API is running, e.g.
#     ai-forecast serve --port 8000
# or
#     docker compose up api
#
# Usage:
#     ./examples/test_api_flow.sh                # defaults to localhost:8000
#     BASE_URL=http://host:port ./test_api_flow.sh
#
# Exits 0 on success, non-zero on first failed step.

set -euo pipefail

BASE="${BASE_URL:-http://localhost:8000}"
STORE="${STORE_ID:-S0001}"
DATE="${TARGET_DATE:-2026-04-26}"

hr() { printf '\n\033[1;36m── %s ──\033[0m\n' "$1"; }

hr "health"
curl -fsS "$BASE/health" | jq .

hr "/api/v1/info — what data is loaded"
curl -fsS "$BASE/api/v1/info" | jq '{name, version, default_model, loaded_datasets}'

hr "Screen 0 — stations"
curl -fsS "$BASE/api/v1/stations" | jq '.[] | {station_id, station_name, positions, primary_channel}'

hr "Screen 0 — stores"
curl -fsS "$BASE/api/v1/stores" | jq '.[0:3]'

hr "Screen 1 — crew @ $STORE"
curl -fsS "$BASE/api/v1/stores/$STORE/crew" \
    | jq '.[0:3] | .[] | {employee_id, employee_name, role, skills}'

hr "Screen 2a — external context on $DATE"
curl -fsS "$BASE/api/v1/context?store_id=$STORE&date=$DATE" \
    | jq '{day_of_week, factors: [.factors[] | {kind,label,source}], channel_multipliers}'

hr "Screen 2b — AI staffing suggestion"
STAFFING=$(curl -fsS -X POST "$BASE/api/v1/forecast/staffing" \
    -H 'content-type: application/json' \
    -d "{\"store_id\":\"$STORE\",\"date\":\"$DATE\",\"demo_mode\":true}")
echo "$STAFFING" | jq '{
    store_id, date, day_of_week, model_used, generation_ms,
    cells: [.cells[] | {station_id, shift, ai_recommended, confidence, reason_short}]
}'

hr "Screen 3 — save a deployment (manager accepts AI grid)"
CELLS=$(echo "$STAFFING" | jq '[.cells[] | {station_id, shift, ai_recommended, assigned_employee_ids: []}]')
DEP=$(curl -fsS -X POST "$BASE/api/v1/deployments" \
    -H 'content-type: application/json' \
    -d "{\"store_id\":\"$STORE\",\"date\":\"$DATE\",\"cells\":$CELLS}")
DEP_ID=$(echo "$DEP" | jq -r '.deployment_id')
echo "created deployment: $DEP_ID"

hr "Screen 4 — deployment summary"
curl -fsS "$BASE/api/v1/deployments/$DEP_ID/summary" | jq .

hr "Screen 5 — list saved deployments @ $STORE"
curl -fsS "$BASE/api/v1/deployments?store_id=$STORE" \
    | jq '.[] | {deployment_id, date, created_at}'

hr "cleanup"
curl -fsS -X DELETE -o /dev/null -w "DELETE /deployments/$DEP_ID → HTTP %{http_code}\n" \
    "$BASE/api/v1/deployments/$DEP_ID"

printf '\n\033[1;32m✓ All screens exercised successfully.\033[0m\n'
