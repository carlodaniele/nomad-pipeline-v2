#!/usr/bin/env python3
"""
Telegram webhook handler for nomad-pipeline-v2.

Buffers photo and text messages per chat session.
Dispatches a GitHub Actions pipeline run on voice/audio message.
"""

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from flask import Flask, request, abort

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
ALLOWED_CHAT_IDS = {
    c.strip()
    for c in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
    if c.strip()
}
GH_TOKEN = os.environ["GH_DISPATCH_TOKEN"]
GH_REPO = os.environ["GH_REPO"]
ADAPTER = os.environ.get("PIPELINE_ADAPTER", "wordpress")
SESSION_DIR = Path(os.environ.get("SESSION_DIR", "/tmp/nomad-sessions"))
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SESSION_TTL = int(os.environ.get("SESSION_TTL_SECONDS", "86400"))

_TGAPI = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _http_post(url: str, payload: dict, headers: dict | None = None) -> dict | None:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": {}}
    except urllib.error.URLError:
        return None


def tg_send(chat_id: str, text: str) -> None:
    _http_post(f"{_TGAPI}/sendMessage", {"chat_id": chat_id, "text": text})


def _session_path(chat_id: str) -> Path:
    return SESSION_DIR / f"{chat_id}.json"


def load_session(chat_id: str) -> dict:
    path = _session_path(chat_id)
    if path.exists():
        data = json.loads(path.read_text())
        if time.time() - data.get("updated_at", 0) < SESSION_TTL:
            return data
    return {"chat_id": chat_id, "images": [], "context": [], "updated_at": time.time()}


def save_session(session: dict) -> None:
    session["updated_at"] = time.time()
    _session_path(session["chat_id"]).write_text(json.dumps(session))


def clear_session(chat_id: str) -> None:
    path = _session_path(chat_id)
    if path.exists():
        path.unlink()


def dispatch_pipeline(payload: dict) -> bool:
    result = _http_post(
        f"https://api.github.com/repos/{GH_REPO}/dispatches",
        {"event_type": "telegram_audio", "client_payload": payload},
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    return result is not None and result["status"] == 204


@app.post("/telegram")
def telegram_webhook():
    if WEBHOOK_SECRET:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            abort(403)

    update = request.get_json(silent=True)
    if not update:
        return "", 200

    message = update.get("message") or update.get("edited_message")
    if not message:
        return "", 200

    chat_id = str(message["chat"]["id"])

    # Silently reject unauthorized senders
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return "", 200

    text = message.get("text", "")

    # /reset command: clear session
    if text.startswith("/reset"):
        clear_session(chat_id)
        tg_send(chat_id, "Session cleared.")
        return "", 200

    # /status command: show session state
    if text.startswith("/status"):
        session = load_session(chat_id)
        imgs = len(session["images"])
        ctx = len(session["context"])
        tg_send(chat_id, f"Session: {imgs} image(s), {ctx} context message(s) buffered.")
        return "", 200

    session = load_session(chat_id)

    # Photo
    if "photo" in message:
        file_id = message["photo"][-1]["file_id"]
        session["images"].append(file_id)
        save_session(session)
        count = len(session["images"])
        tg_send(chat_id, f"Image received ({count} total in session).")
        return "", 200

    # Plain text context
    if text and not text.startswith("/"):
        session["context"].append(text)
        save_session(session)
        tg_send(chat_id, "Context added.")
        return "", 200

    # Voice / audio / document — triggers the pipeline
    audio_obj = message.get("voice") or message.get("audio") or message.get("document")
    if audio_obj:
        file_id = audio_obj["file_id"]
        mime_type = audio_obj.get("mime_type", "audio/ogg")
        message_id = str(message["message_id"])
        external_run_id = f"tg-{chat_id}-{message_id}"

        tg_send(chat_id, "Processing started… I'll notify you when done.")

        ok = dispatch_pipeline({
            "chat_id": chat_id,
            "external_run_id": external_run_id,
            "audio_file_id": file_id,
            "audio_mime_type": mime_type,
            "image_file_ids": session["images"],
            "context_text": "\n".join(session["context"]),
            "adapter": ADAPTER,
        })

        if ok:
            clear_session(chat_id)
        else:
            tg_send(chat_id, "Failed to start pipeline. Please try again.")

        return "", 200

    return "", 200


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
