"""
Nomad Pipeline v2 - Telegram Ingest (polling mode)

Does not use a real Telegram webhook (that would require an always-on
server). Periodically polls `getUpdates` and downloads media files
received from authorized chats into GH_INPUT_FOLDER (default: media-input/).

Meant to be run from a scheduled GitHub Actions workflow
(see .github/workflows/telegram-poll.yml).
"""

import os
import re
import mimetypes
import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_IDS = {
    c.strip() for c in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if c.strip()
}
INPUT_FOLDER = os.getenv("GH_INPUT_FOLDER", "media-input")
STATE_FILE = os.getenv("TELEGRAM_STATE_FILE", ".state/telegram_offset.txt")

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
FILE_BASE = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"


def ensure_polling_mode():
    """getUpdates fails with 409 Conflict if a webhook is still active."""
    resp = requests.get(f"{API_BASE}/getWebhookInfo", timeout=30)
    resp.raise_for_status()
    info = resp.json().get("result", {})
    if info.get("url"):
        print(f"[Telegram] Removing leftover webhook: {info['url']}")
        requests.get(f"{API_BASE}/deleteWebhook", timeout=30)


def read_offset() -> int:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            content = f.read().strip()
            if content.isdigit():
                return int(content)
    return 0


def write_offset(offset: int) -> None:
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        f.write(str(offset))


def get_updates(offset: int):
    params = {"timeout": 0}
    if offset:
        params["offset"] = offset
    resp = requests.get(f"{API_BASE}/getUpdates", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"getUpdates failed: {data}")
    return data["result"]


def download_telegram_file(file_id: str, dest_path: str) -> None:
    resp = requests.get(f"{API_BASE}/getFile", params={"file_id": file_id}, timeout=30)
    resp.raise_for_status()
    file_path = resp.json()["result"]["file_path"]

    file_resp = requests.get(f"{FILE_BASE}/{file_path}", timeout=120)
    file_resp.raise_for_status()

    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(file_resp.content)


def safe_name(chat_id: str, message_id: int, suggested_name, fallback_ext: str) -> str:
    if suggested_name:
        base, ext = os.path.splitext(suggested_name)
        ext = ext or fallback_ext
        base = re.sub(r"[^A-Za-z0-9_-]", "_", base)
        return f"{chat_id}_{message_id}_{base}{ext}"
    return f"{chat_id}_{message_id}{fallback_ext}"


def extract_media(message: dict):
    """Returns (file_id, suggested_name, extension) or None."""
    if "voice" in message:
        v = message["voice"]
        return v["file_id"], None, ".oga"

    if "audio" in message:
        a = message["audio"]
        name = a.get("file_name")
        ext = os.path.splitext(name)[1] if name else ".mp3"
        return a["file_id"], name, ext

    if "document" in message:
        d = message["document"]
        mime = d.get("mime_type", "") or ""
        name = d.get("file_name")
        ext = os.path.splitext(name)[1] if name else (mimetypes.guess_extension(mime) or "")
        if mime.startswith("audio/") or mime.startswith("image/"):
            return d["file_id"], name, ext

    if "photo" in message and message["photo"]:
        # Telegram sends multiple resolutions of the same photo: keep the largest (last) one.
        p = message["photo"][-1]
        return p["file_id"], None, ".jpg"

    return None


def main():
    ensure_polling_mode()

    offset = read_offset()
    updates = get_updates(offset)

    if not updates:
        print("[Telegram] No new updates.")
        write_offset(offset)
        return

    saved_files = []
    max_update_id = offset - 1

    for update in updates:
        update_id = update["update_id"]
        max_update_id = max(max_update_id, update_id)

        message = update.get("message") or update.get("channel_post")
        if not message:
            continue

        chat_id = str(message.get("chat", {}).get("id"))
        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            print(f"[Telegram] Ignoring unauthorized chat: {chat_id}")
            continue

        media = extract_media(message)
        if not media:
            continue

        file_id, suggested_name, ext = media
        filename = safe_name(chat_id, message["message_id"], suggested_name, ext)
        dest_path = os.path.join(INPUT_FOLDER, filename)

        print(f"[Telegram] Downloading {filename} from chat {chat_id}...")
        download_telegram_file(file_id, dest_path)
        saved_files.append(dest_path)

    # Advance the offset even for ignored/unauthorized updates,
    # otherwise they would be re-read on every subsequent poll.
    write_offset(max_update_id + 1)

    if saved_files:
        print(f"[Telegram] {len(saved_files)} files saved in '{INPUT_FOLDER}': {saved_files}")
    else:
        print("[Telegram] No valid media file in the new updates.")


if __name__ == "__main__":
    main()
