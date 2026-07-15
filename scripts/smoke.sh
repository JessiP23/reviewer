#!/usr/bin/env sh
set -eu

API_URL="${API_URL:-http://localhost:8000}"
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

curl --fail --silent --show-error "${API_URL}/health"
printf '\n'

ACCEPTED="$(curl --fail --silent --show-error \
  -F "file=@${PROJECT_ROOT}/examples/demo-financials.csv" \
  "${API_URL}/v1/reviews")"
printf '%s\n' "$ACCEPTED"

REVIEW_ID="$(printf '%s' "$ACCEPTED" | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["id"])')"
QUERY_PAYLOAD="$(REVIEW_ID="$REVIEW_ID" python3 -c \
  'import json,os; print(json.dumps({"query": "query Smoke($id: ID!) { review(id: $id) { id status findings { code } metrics { key } error } }", "variables": {"id": os.environ["REVIEW_ID"]}}))')"

attempt=0
while [ "$attempt" -lt 60 ]; do
  RESULT="$(curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data "$QUERY_PAYLOAD" \
    "${API_URL}/graphql")"
  STATUS="$(printf '%s' "$RESULT" | python3 -c \
    'import json,sys; print(json.load(sys.stdin)["data"]["review"]["status"])')"
  case "$STATUS" in
    completed|needs_review)
      printf '%s\n' "$RESULT"
      exit 0
      ;;
    failed)
      printf '%s\n' "$RESULT" >&2
      exit 1
      ;;
  esac
  attempt=$((attempt + 1))
  sleep 1
done

printf 'Review %s did not finish within 60 seconds.\n' "$REVIEW_ID" >&2
exit 1
