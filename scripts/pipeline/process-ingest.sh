#!/usr/bin/env bash
# Process one staged ingest session from repository files.
# Expects AUDIO_PATH relative to repo root (e.g. uploads/chat-123/audio.ogg).
set -euo pipefail

: "${AUDIO_PATH:?}"
: "${ADAPTER:=wordpress}"
: "${EXTERNAL_RUN_ID:=ingest-local}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ABS_AUDIO_PATH="${ROOT_DIR}/${AUDIO_PATH}"

if [[ ! -f "${ABS_AUDIO_PATH}" ]]; then
  echo "ERROR: audio file not found: ${AUDIO_PATH}" >&2
  exit 1
fi

SESSION_DIR="$(dirname "${ABS_AUDIO_PATH}")"
SESSION_NAME="$(basename "${SESSION_DIR}")"
WORK_DIR="$(mktemp -d)"
ADAPTER_SCRIPT="${ROOT_DIR}/adapters/${ADAPTER}/process.sh"
UPLOADS_DIR="${ROOT_DIR}/uploads"

cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

if [[ ! -x "${ADAPTER_SCRIPT}" ]]; then
  echo "ERROR: adapter '${ADAPTER}' not found: ${ADAPTER_SCRIPT}" >&2
  exit 1
fi

mime_from_ext() {
  local path="$1"
  case "${path##*.}" in
    mp3) echo "audio/mpeg" ;;
    m4a) echo "audio/mp4" ;;
    wav) echo "audio/wav" ;;
    webm) echo "audio/webm" ;;
    ogg|oga) echo "audio/ogg" ;;
    *) echo "audio/ogg" ;;
  esac
}

AUDIO_MIME_TYPE="$(mime_from_ext "${ABS_AUDIO_PATH}")"
AUDIO_FILE="${WORK_DIR}/audio.${ABS_AUDIO_PATH##*.}"
cp "${ABS_AUDIO_PATH}" "${AUDIO_FILE}"

IMAGE_COUNT=0
CONTEXT_TEXT=""
FILES_TO_ARCHIVE=()

# Legacy mode: files directly under uploads/.
if [[ "${SESSION_DIR}" == "${UPLOADS_DIR}" ]]; then
  shopt -s nullglob
  img_index=0
  for img in "${UPLOADS_DIR}"/*.jpg "${UPLOADS_DIR}"/*.jpeg "${UPLOADS_DIR}"/*.png "${UPLOADS_DIR}"/*.webp; do
    cp "${img}" "${WORK_DIR}/img_${img_index}.jpg"
    FILES_TO_ARCHIVE+=("${img}")
    img_index=$((img_index + 1))
  done
  IMAGE_COUNT="${img_index}"

  for txt in "${UPLOADS_DIR}"/*.txt; do
    CONTEXT_TEXT+="$(cat "${txt}")"$'\n'
    FILES_TO_ARCHIVE+=("${txt}")
  done
  shopt -u nullglob

  FILES_TO_ARCHIVE+=("${ABS_AUDIO_PATH}")
else
  # Session-folder mode: keep compatibility with uploads/<session_id>/ layout.
  img_index=0
  shopt -s nullglob
  for img in "${SESSION_DIR}"/*.jpg "${SESSION_DIR}"/*.jpeg "${SESSION_DIR}"/*.png "${SESSION_DIR}"/*.webp; do
    cp "${img}" "${WORK_DIR}/img_${img_index}.jpg"
    img_index=$((img_index + 1))
  done
  shopt -u nullglob
  IMAGE_COUNT="${img_index}"

  if [[ -f "${SESSION_DIR}/context.txt" ]]; then
    CONTEXT_TEXT="$(cat "${SESSION_DIR}/context.txt")"
  fi
fi

RESULT_JSON=$(AUDIO_FILE="${AUDIO_FILE}" \
  AUDIO_MIME_TYPE="${AUDIO_MIME_TYPE}" \
  IMAGE_DIR="${WORK_DIR}" \
  IMAGE_COUNT="${IMAGE_COUNT}" \
  CONTEXT_TEXT="${CONTEXT_TEXT}" \
  EXTERNAL_RUN_ID="${EXTERNAL_RUN_ID}" \
  bash "${ADAPTER_SCRIPT}")

STATUS=$(echo "${RESULT_JSON}" | jq -r '.status // "failed"')
POST_URL=$(echo "${RESULT_JSON}" | jq -r '.post_url // empty')
ERROR_MSG=$(echo "${RESULT_JSON}" | jq -r '.error.message // "unknown error"')

TARGET_ROOT="processed"
if [[ "${STATUS}" != "completed" ]]; then
  TARGET_ROOT="failed"
fi

mkdir -p "${ROOT_DIR}/${TARGET_ROOT}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET_DIR="${ROOT_DIR}/${TARGET_ROOT}/${SESSION_NAME}-${TS}"

if [[ "${SESSION_DIR}" == "${UPLOADS_DIR}" ]]; then
  for src in "${FILES_TO_ARCHIVE[@]}"; do
    [[ -f "${src}" ]] || continue
    base="$(basename "${src}")"
    dest="${ROOT_DIR}/${TARGET_ROOT}/${TS}-${base}"
    mv "${src}" "${dest}"
  done
else
  if [[ -e "${TARGET_DIR}" ]]; then
    TARGET_DIR="${TARGET_DIR}-$$"
  fi
  mv "${SESSION_DIR}" "${TARGET_DIR}"
fi

echo "Session '${SESSION_NAME}' -> ${TARGET_ROOT}"
if [[ "${STATUS}" == "completed" ]]; then
  echo "Post published: ${POST_URL}"
else
  echo "Adapter failed: ${ERROR_MSG}" >&2
  exit 1
fi
