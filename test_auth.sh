#!/usr/bin/env bash
set -e
echo "Logging in to backend..."
RESP=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=admin&password=admin")
echo "Response: $RESP"
TOKEN=$(echo "$RESP" | python -c "import sys,json; obj=json.load(sys.stdin); print(obj.get('access_token',''))")
if [ -z "$TOKEN" ]; then
  echo "No token received"
  exit 1
fi
echo "Token received (truncated): ${TOKEN:0:20}..."
echo "Calling admin-only endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/only | jq .
