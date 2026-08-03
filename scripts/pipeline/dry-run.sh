#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_ID="run_$(date +%s)"
OUT_DIR="$ROOT_DIR/reports"
OUT_FILE="$OUT_DIR/dry-run-${RUN_ID}.json"

mkdir -p "$OUT_DIR"

echo "[1/6] receive_telegram_images"
echo "[2/6] receive_telegram_context_text"
echo "[3/6] receive_telegram_audio"
echo "[4/6] transcribe_audio"
echo "[5/6] generate_content"
echo "[6/6] publish_via_adapter"

cat > "$OUT_FILE" <<JSON
{
  "contract_version": "1.0.0",
  "run_id": "$RUN_ID",
  "status": "completed",
  "quality_flags": ["dry_run"],
  "processing_timestamps": {
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  },
  "debug_reference_id": "dbg_$RUN_ID"
}
JSON

echo "[OK] Dry run report: $OUT_FILE"
