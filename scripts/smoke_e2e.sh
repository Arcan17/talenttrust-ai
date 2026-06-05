#!/usr/bin/env bash
#
# TalentTrust AI — end-to-end smoke test.
#
# Exercises the full MVP flow against a running backend:
#   register -> login -> create vacancy -> upload CV (+consent) -> generate dossier
#   -> get score -> record human decision -> export PDF
#
# Deterministic & offline: the backend must run with LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock.
# Idempotent: uses a unique org/email per run (timestamp), so it can be run repeatedly.
#
# Usage:
#   BASE=http://localhost:8000 ./scripts/smoke_e2e.sh
#
# Expected: every step prints "OK" and the final line is "SMOKE E2E PASSED".

set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
API="$BASE/api/v1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CV="$SCRIPT_DIR/sample_cv.pdf"
STAMP="$(date +%s)"
EMAIL="admin+${STAMP}@smoke.test.example"
ORG="SmokeOrg-${STAMP}"
PASS="supersecret1"

jget() { python3 -c "import sys,json;print(json.load(sys.stdin)$1)"; }

echo "→ Backend: $BASE"
echo "→ Sample CV: $CV"
[ -f "$CV" ] || { echo "FAIL: missing $CV"; exit 1; }

echo "1) register org_admin ($EMAIL)"
TOK=$(curl -fsS -X POST "$API/auth/register" -H 'content-type: application/json' \
  -d "{\"organization_name\":\"$ORG\",\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | jget "['access_token']")
echo "   OK (token len ${#TOK})"

echo "2) login"
curl -fsS -X POST "$API/auth/login" -H 'content-type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" >/dev/null
echo "   OK (200)"

echo "3) create vacancy"
VID=$(curl -fsS -X POST "$API/vacancies" -H "Authorization: Bearer $TOK" \
  -H 'content-type: application/json' \
  -d '{"title":"Python Backend Developer","required_skills":["python","fastapi"],"desired_skills":["docker"],"modality":"remote","country":"CL","seniority":"senior"}' \
  | jget "['id']")
echo "   OK (vacancy $VID)"

echo "4) upload candidate (CV + consent)"
CID=$(curl -fsS -X POST "$API/vacancies/$VID/candidates" -H "Authorization: Bearer $TOK" \
  -F "file=@$CV;type=application/pdf" \
  -F "consent_version=v1" -F "consent_scope=professional-evaluation" \
  -F "display_name=Jane Doe" | jget "['id']")
echo "   OK (candidate $CID)"

echo "5) generate dossier"
REC=$(curl -fsS -X POST "$API/candidates/$CID/dossier" -H "Authorization: Bearer $TOK" \
  | jget "['recommendation']")
echo "   OK (recommendation=$REC)"

echo "6) get score"
VAL=$(curl -fsS "$API/candidates/$CID/score" -H "Authorization: Bearer $TOK" | jget "['value']")
echo "   OK (score=$VAL/100)"

echo "7) record human decision"
OUT=$(curl -fsS -X POST "$API/candidates/$CID/decision" -H "Authorization: Bearer $TOK" \
  -H 'content-type: application/json' \
  -d '{"human_outcome":"interview","note":"Strong fit"}' | jget "['human_outcome']")
echo "   OK (human_outcome=$OUT)"

echo "8) export dossier PDF"
PDF="$(mktemp -t tt_smoke_XXXX).pdf"
CODE=$(curl -fsS -X POST "$API/candidates/$CID/dossier/export" -H "Authorization: Bearer $TOK" \
  -o "$PDF" -w "%{http_code}")
MAGIC=$(head -c 4 "$PDF")
SIZE=$(wc -c < "$PDF" | tr -d ' ')
rm -f "$PDF"
[ "$CODE" = "200" ] && [ "$MAGIC" = "%PDF" ] || { echo "FAIL: export http=$CODE magic=$MAGIC"; exit 1; }
echo "   OK (http=$CODE, ${SIZE} bytes, magic=$MAGIC)"

echo
echo "SMOKE E2E PASSED"
