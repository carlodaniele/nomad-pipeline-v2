#!/usr/bin/env bash
# WordPress adapter for nomad-pipeline-v2.
# Uploads audio and images to WP media, then calls the Ability with media IDs.
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
MEDIA_PATH="/wp-json/wp/v2/media"
AUTH_HEADER="Authorization: Basic $(printf '%s' "${WP_ABILITY_AUTH}" | base64 | tr -d '\n')"

log() { echo "[wp-adapter] $*" >&2; }

# ── Upload audio to WP media library ─────────────────────────────────────────
log "Uploading audio to WP media"
AUDIO_FILENAME="$(basename "${AUDIO_FILE}")"
AUDIO_MEDIA_ID=$(curl -s -X POST \
  "${WP_ABILITY_URL}${MEDIA_PATH}" \
  -H "${AUTH_HEADER}" \
  -H "Content-Disposition: attachment; filename=\"${AUDIO_FILENAME}\"" \
  -H "Content-Type: ${AUDIO_MIME_TYPE}" \
  --data-binary "@${AUDIO_FILE}" \
  | jq -r '.id // empty')

if [[ -z "${AUDIO_MEDIA_ID}" ]]; then
  log "ERROR: audio upload failed"
  echo '{"status":"failed","error":{"code":"publish_failed","message":"Audio upload to WP media failed.","retryable":false}}'
  exit 1
fi
log "Audio media ID: ${AUDIO_MEDIA_ID}"

# ── Upload images to WP media library ────────────────────────────────────────
GALLERY_IDS="[]"
if [[ "${IMAGE_COUNT}" -gt 0 && -n "${IMAGE_DIR}" ]]; then
  IDS_COLLECTED=()
  for i in $(seq 0 $((IMAGE_COUNT - 1))); do
    IMG_FILE="${IMAGE_DIR}/img_${i}.jpg"
    [[ -f "${IMG_FILE}" ]] || continue
    log "Uploading image ${i}"
    WP_MEDIA_ID=$(curl -s -X POST \
      "${WP_ABILITY_URL}${MEDIA_PATH}" \
      -H "${AUTH_HEADER}" \
      -H "Content-Disposition: attachment; filename=\"telegram_img_${i}.jpg\"" \
      -H "Content-Type: image/jpeg" \
      --data-binary "@${IMG_FILE}" \
      | jq -r '.id // empty')
    if [[ -n "${WP_MEDIA_ID}" ]]; then
      IDS_COLLECTED+=("${WP_MEDIA_ID}")
      log "Image media ID: ${WP_MEDIA_ID}"
    fi
  done
  if [[ ${#IDS_COLLECTED[@]} -gt 0 ]]; then
    GALLERY_IDS=$(printf '%s\n' "${IDS_COLLECTED[@]}" | jq -R 'tonumber' | jq -s '.')
  fi
fi
log "Gallery IDs: ${GALLERY_IDS}"

# ── Build Ability payload (tiny — only IDs, no binary data) ──────────────────
PAYLOAD_FILE="$(mktemp)"
jq -n \
  --arg contract_version "1.0.0" \
  --arg external_run_id "${EXTERNAL_RUN_ID}" \
  --arg context "${CONTEXT_TEXT}" \
  --argjson audio_media_id "${AUDIO_MEDIA_ID}" \
  --argjson gallery_ids "${GALLERY_IDS}" \
  '{
    "contract_version": $contract_version,
    "external_run_id": $external_run_id,
    "source": "telegram",
    "source_metadata": {
      "telegram_context": $context
    },
    "audio": {
      "media_id": $audio_media_id
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
  }' > "${PAYLOAD_FILE}"

# ── Call the Ability endpoint ─────────────────────────────────────────────────
log "Calling Ability endpoint: ${WP_ABILITY_URL}${ABILITY_PATH}"
RESPONSE=$(curl -s --max-time 120 -X POST \
  "${WP_ABILITY_URL}${ABILITY_PATH}" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  --data-binary "@${PAYLOAD_FILE}")

rm -f "${PAYLOAD_FILE}"
log "Ability response: ${RESPONSE}"

echo "${RESPONSE}"

: "${WP_ABILITY_URL:?}"
: "${WP_ABILITY_AUTH:?}"
: "${TELEGRAM_BOT_TOKEN:?}"
: "${AUDIO_FILE_ID:?}"
: "${EXTERNAL_RUN_ID:?}"

IMAGE_DIR="${IMAGE_DIR:-}"
IMAGE_COUNT="${IMAGE_COUNT:-0}"
CONTEXT_TEXT="${CONTEXT_TEXT:-}"

ABILITY_PATH="/wp-json/wp-abilities/v1/abilities/nomad-pipeline-audio-to-draft/audio-to-post/run"
TGAPI="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"
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

# ── Get Telegram audio signed URL ─────────────────────────────────────────────
log "Resolving audio URL"
FILE_PATH=$(curl -sf "${TGAPI}/getFile?file_id=${AUDIO_FILE_ID}" | jq -r '.result.file_path')
AUDIO_URL="https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${FILE_PATH}"
log "Audio URL resolved"

# ── Build Ability payload ─────────────────────────────────────────────────────
PAYLOAD_FILE="$(mktemp)"
jq -n \
  --arg contract_version "1.0.0" \
  --arg external_run_id "${EXTERNAL_RUN_ID}" \
  --arg audio_url "${AUDIO_URL}" \
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
      "signed_url": $audio_url
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
  }' > "${PAYLOAD_FILE}"

# ── Call the Ability endpoint ─────────────────────────────────────────────────
log "Calling Ability endpoint: ${WP_ABILITY_URL}${ABILITY_PATH}"
RESPONSE=$(curl -s --max-time 120 -X POST \
  "${WP_ABILITY_URL}${ABILITY_PATH}" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  --data "@${PAYLOAD_FILE}")

rm -f "${PAYLOAD_FILE}"
log "Ability response: ${RESPONSE}"

# Output canonical result to stdout (consumed by run.sh)
echo "${RESPONSE}"
