#!/usr/bin/env bash
# WordPress adapter for nomad-pipeline-v2.
# Uploads images to WP media library, then calls the Ability endpoint with base64 audio.
# Outputs a canonical result JSON to stdout.
set -euo pipefail

: "${WP_ABILITY_URL:?}"
: "${WP_ABILITY_AUTH:?}"
: "${AUDIO_FILE:?}"
: "${AUDIO_MIME_TYPE:?}"
: "${EXTERNAL_RUN_ID:?}"

IMAGE_DIR="${IMAGE_DIR:-}"
IMAGE_COUNT="${IMAGE_COUNT:-0}"
CONTEXT_TEXT="${CONTEXT_TEXT:-}"

ABILITY_PATH="/wp-json/wp-abilities/v1/abilities/nomad-pipeline-audio-to-draft/audio-to-post/run"
AUTH_HEADER="Authorization: Basic $(printf '%s' "${WP_ABILITY_AUTH}" | base64 | tr -d '\n')"

log() { echo "[wp-adapter] $*" >&2; }

# ── Upload images to WP media library ────────────────────────────────────────
GALLERY_IDS="[]"
if [[ "${IMAGE_COUNT}" -gt 0 && -n "${IMAGE_DIR}" ]]; then
  IDS_COLLECTED=()
  for i in $(seq 0 $((IMAGE_COUNT - 1))); do
    IMG_FILE="${IMAGE_DIR}/img_${i}.jpg"
    [[ -f "${IMG_FILE}" ]] || continue
    log "Uploading image ${i}"
    WP_MEDIA_ID=$(curl -s -X POST \
      "${WP_ABILITY_URL}/wp-json/wp/v2/media" \
      -H "${AUTH_HEADER}" \
      -H "Content-Disposition: attachment; filename=\"telegram_img_${i}.jpg\"" \
      -H "Content-Type: image/jpeg" \
      --data-binary "@${IMG_FILE}" \
      | jq -r '.id // empty')
    if [[ -n "${WP_MEDIA_ID}" ]]; then
      IDS_COLLECTED+=("${WP_MEDIA_ID}")
      log "Media ID: ${WP_MEDIA_ID}"
    fi
  done
  if [[ ${#IDS_COLLECTED[@]} -gt 0 ]]; then
    GALLERY_IDS=$(printf '%s\n' "${IDS_COLLECTED[@]}" | jq -R 'tonumber' | jq -s '.')
  fi
fi
log "Gallery IDs: ${GALLERY_IDS}"

# ── Encode audio as base64 ────────────────────────────────────────────────────
log "Encoding audio"
AUDIO_BASE64=$(base64 "${AUDIO_FILE}" | tr -d '\n')

# ── Build Ability payload ─────────────────────────────────────────────────────
PAYLOAD=$(jq -n \
  --arg contract_version "1.0.0" \
  --arg external_run_id "${EXTERNAL_RUN_ID}" \
  --arg audio_base64 "${AUDIO_BASE64}" \
  --arg mime_type "${AUDIO_MIME_TYPE}" \
  --arg context "${CONTEXT_TEXT}" \
  --argjson gallery_ids "${GALLERY_IDS}" \
  '{
    "contract_version": $contract_version,
    "external_run_id": $external_run_id,
    "source": "telegram",
    "source_metadata": {
      "telegram_context": $context
    },
    "audio": {
      "base64": $audio_base64,
      "mime_type": $mime_type
    },
    "publish_options": {
      "status": "draft",
      "post_type": "post"
    },
    "media_options": (
      if ($gallery_ids | length) > 0
      then {"gallery_image_ids": $gallery_ids}
      else {}
      end
    )
  }')

# ── Call the Ability endpoint ─────────────────────────────────────────────────
log "Calling Ability endpoint"
RESPONSE=$(curl -s -X POST \
  "${WP_ABILITY_URL}${ABILITY_PATH}" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

# Output canonical result to stdout (consumed by run.sh)
echo "${RESPONSE}"
