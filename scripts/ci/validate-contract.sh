#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

json_files=(
  "$ROOT_DIR/docs/contracts/schemas/input-v1.json"
  "$ROOT_DIR/docs/contracts/schemas/output-v1.json"
  "$ROOT_DIR/docs/contracts/examples/request-valid.json"
  "$ROOT_DIR/docs/contracts/examples/response-success.json"
  "$ROOT_DIR/docs/contracts/examples/response-failed.json"
)

if ! command -v jq >/dev/null 2>&1; then
  echo "[FAIL] jq not found. Install jq to run contract validation."
  exit 1
fi

failed=0
for file in "${json_files[@]}"; do
  if jq empty "$file" >/dev/null 2>&1; then
    echo "[OK] Valid JSON: ${file#$ROOT_DIR/}"
  else
    echo "[FAIL] Invalid JSON: ${file#$ROOT_DIR/}"
    failed=1
  fi
done

if [[ "$failed" -eq 1 ]]; then
  echo "[RESULT] Contract validation FAILED"
  exit 1
fi

echo "[RESULT] Contract validation PASSED"
