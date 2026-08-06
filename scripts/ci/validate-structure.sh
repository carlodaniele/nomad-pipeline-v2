#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

required_dirs=(
  "$ROOT_DIR/core"
  "$ROOT_DIR/adapters/wordpress"
  "$ROOT_DIR/adapters/astro"
  "$ROOT_DIR/docs/contracts/schemas"
  "$ROOT_DIR/docs/contracts/examples"
  "$ROOT_DIR/scripts/ci"
  "$ROOT_DIR/scripts/pipeline"
)

required_files=(
  "$ROOT_DIR/README.md"
  "$ROOT_DIR/requirements.txt"
  "$ROOT_DIR/.env.example"
  "$ROOT_DIR/docs/contracts/ability-audio-to-post-v1.md"
  "$ROOT_DIR/docs/contracts/error-model.md"
  "$ROOT_DIR/docs/contracts/schemas/input-v1.json"
  "$ROOT_DIR/docs/contracts/schemas/output-v1.json"
  "$ROOT_DIR/docs/contracts/examples/request-valid.json"
  "$ROOT_DIR/docs/contracts/examples/response-success.json"
  "$ROOT_DIR/docs/contracts/examples/response-failed.json"
  "$ROOT_DIR/scripts/pipeline/process-ingest.sh"
  "$ROOT_DIR/adapters/wordpress/process.sh"
  "$ROOT_DIR/.github/workflows/ingest-audio.yml"
)

failed=0

for d in "${required_dirs[@]}"; do
  if [[ -d "$d" ]]; then
    echo "[OK] Dir: ${d#$ROOT_DIR/}"
  else
    echo "[FAIL] Missing dir: ${d#$ROOT_DIR/}"
    failed=1
  fi
done

for f in "${required_files[@]}"; do
  if [[ -s "$f" ]]; then
    echo "[OK] File: ${f#$ROOT_DIR/}"
  else
    echo "[FAIL] Missing or empty file: ${f#$ROOT_DIR/}"
    failed=1
  fi
done

if [[ "$failed" -eq 1 ]]; then
  echo "[RESULT] Structure validation FAILED"
  exit 1
fi

echo "[RESULT] Structure validation PASSED"
