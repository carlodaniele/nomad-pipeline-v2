#!/usr/bin/env bash
# Core pipeline orchestrator. Runs inside GitHub Actions (pipeline-run.yml).
# Downloads audio and images from Telegram, then delegates to the CMS adapter.
set -euo pipefail

# ── Required env vars (injected by GitHub Actions) ────────────────────────────
: "${TELEGRAM_BOT_TOKEN:?}"
: "${CHAT_ID:?}"
: "${EXTERNAL_RUN_ID:?}"
: "${AUDIO_FILE_ID:?}"
: "${AUDIO_MIME_TYPE:?}"
: "${ADAPTER:?}"

IMAGE_FILE_IDS="${IMAGE_FILE_IDS:-[]}"
CONTEXT_TEXT="${CONTEXT_TEXT:-}"

TGAPI="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"
WORK_DIR="$(mktemp -d)"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

log()     { echo "[$(date -u +%H:%M:%S)] $*"; }
tg_send() { curl -s -X POST "${TGAPI}/sendMessage" -H "Content-Type: application/json" \
              -d "$(jq -n --arg c "${CHAT_ID}" --arg t "$1" '{"chat_id":$c,"text":$t}')" > /dev/null; }

tg_download() {
  local file_id="$1" dest="$2"
  local file_path
  file_path=$(curl -sf "${TGAPI}/getFile?file_id=${file_id}" | jq -r '.result.file_path')
  curl -sf "https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${file_path}" -o "$dest"
}

on_error() {
  tg_send "Pipeline error (run: ${EXTERNAL_RUN_ID}). Check GitHub Actions logs."
  rm -rf "${WORK_DIR}"
}
trap on_error ERR

# ── Step 1: Download audio ────────────────────────────────────────────────────
log "1/3 Downloading audio"
AUDIO_EXT="ogg"
case "${AUDIO_MIME_TYPE}" in
  audio/mpeg) AUDIO_EXT="mp3"  ;;
  audio/mp4)  AUDIO_EXT="m4a"  ;;
  audio/wav)  AUDIO_EXT="wav"  ;;
  audio/webm) AUDIO_EXT="webm" ;;
esac
AUDIO_FILE="${WORK_DIR}/audio.${AUDIO_EXT}"
tg_download "${AUDIO_FILE_ID}" "${AUDIO_FILE}"
log "Audio saved: ${AUDIO_FILE}"

# ── Step 2: Download images ───────────────────────────────────────────────────
log "2/3 Downloading images"
IMG_COUNT=0
while IFS= read -r file_id; do
  [[ -z "${file_id}" || "${file_id}" == "null" ]] && continue
  tg_download "${file_id}" "${WORK_DIR}/img_${IMG_COUNT}.jpg"
  IMG_COUNT=$((IMG_COUNT + 1))
done < <(echo "${IMAGE_FILE_IDS}" | jq -r '.[] // empty' 2>/dev/null || true)
log "Images downloaded: ${IMG_COUNT}"

# ── Step 3: Run adapter ───────────────────────────────────────────────────────
log "3/3 Running adapter: ${ADAPTER}"
ADAPTER_SCRIPT="${ROOT_DIR}/adapters/${ADAPTER}/process.sh"
if [[ ! -x "${ADAPTER_SCRIPT}" ]]; then
  tg_send "Configuration error: adapter '${ADAPTER}' not found."
  exit 1
fi

RESULT=$(AUDIO_FILE="${AUDIO_FILE}" \
         AUDIO_FILE_ID="${AUDIO_FILE_ID}" \
         AUDIO_MIME_TYPE="${AUDIO_MIME_TYPE}" \
         IMAGE_DIR="${WORK_DIR}" \
         IMAGE_COUNT="${IMG_COUNT}" \
         CONTEXT_TEXT="${CONTEXT_TEXT}" \
         EXTERNAL_RUN_ID="${EXTERNAL_RUN_ID}" \
         bash "${ADAPTER_SCRIPT}")

STATUS=$(echo "${RESULT}" | jq -r '.status // empty')
POST_URL=$(echo "${RESULT}" | jq -r '.post_url // empty')
ERROR_MSG=$(echo "${RESULT}" | jq -r '.error.message // empty')
RETRYABLE=$(echo "${RESULT}" | jq -r '.error.retryable // false')

if [[ "${STATUS}" == "completed" && -n "${POST_URL}" ]]; then
  tg_send "Done! Draft published: ${POST_URL}"
else
  if [[ "${RETRYABLE}" == "true" ]]; then
    tg_send "Failed (retryable): ${ERROR_MSG:-unknown error}. You can try sending the audio again."
  else
    tg_send "Failed: ${ERROR_MSG:-unknown error}. Check GitHub Actions logs (run: ${EXTERNAL_RUN_ID})."
  fi
  exit 1
fi

rm -rf "${WORK_DIR}"
log "Pipeline complete."
