#!/usr/bin/env python3
"""Telegram long-polling listener for nomad-pipeline-v2.

Runs inside GitHub Actions.
Buffers images and text per chat_id in memory.
On audio message, uploads session files to `ingest` branch under
`uploads/<session_id>/...`; the audio file push then triggers
the legacy-style ingest workflow.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_IDS = {
    c.strip()
    for c in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
    if c.strip()
}
GH_TOKEN = os.environ.get("GH_INGEST_TOKEN") or os.environ.get("GH_DISPATCH_TOKEN")
GH_REPO = os.environ["GH_REPO"]
INGEST_BRANCH = os.environ.get("INGEST_BRANCH", "ingest")
# Exit before GitHub Actions' 6-hour job limit so self-restart can fire.
MAX_RUNTIME = int(os.environ.get("LISTENER_MAX_RUNTIME", str(5 * 3600 + 30 * 60)))

_TGAPI = f"https://api.telegram.org/bot{BOT_TOKEN}"

# In-memory session store: {chat_id: {"images": [...], "context": [...], "ts": float}}
_sessions: dict[str, dict] = {}
SESSION_TTL = 86400  # seconds; stale sessions are evicted on next access


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _post(url: str, payload: dict, timeout: int = 10, headers: dict | None = None) -> dict | None:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        log(f"HTTP {exc.code} from {url}")
    except Exception as exc:
        log(f"Request error: {exc}")
    return None


def tg_send(chat_id: str, text: str) -> None:
    _post(f"{_TGAPI}/sendMessage", {"chat_id": chat_id, "text": text})


def tg_get_updates(offset: int | None, timeout: int = 55) -> list[dict]:
    params: dict = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    result = _post(f"{_TGAPI}/getUpdates", params, timeout=timeout + 10)
    if result and result.get("ok"):
        return result.get("result", [])
    return []


def _get_json(url: str, timeout: int = 20) -> dict | None:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        log(f"HTTP {exc.code} from {url}")
    except Exception as exc:
        log(f"Request error: {exc}")
    return None


def _get_bytes(url: str, timeout: int = 60) -> bytes | None:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        log(f"HTTP {exc.code} while downloading {url}")
    except Exception as exc:
        log(f"Download error: {exc}")
    return None


def tg_download(file_id: str) -> tuple[bytes, str] | None:
    meta = _get_json(f"{_TGAPI}/getFile?file_id={urllib.parse.quote(file_id)}")
    if not meta or not meta.get("ok"):
        return None
    file_path = meta["result"]["file_path"]
    blob = _get_bytes(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}")
    if blob is None:
        return None
    return blob, file_path


def gh_put_file(path: str, content: bytes, message: str) -> bool:
    if not GH_TOKEN:
        log("Missing GH token for ingest writes.")
        return False

    body = json.dumps({
        "message": message,
        "content": base64.b64encode(content).decode(),
        "branch": INGEST_BRANCH,
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)
    except urllib.error.HTTPError as exc:
        log(f"GitHub upload HTTP {exc.code} for {path}")
        return False


def _session(chat_id: str) -> dict:
    s = _sessions.get(chat_id)
    if s is None or time.time() - s["ts"] > SESSION_TTL:
        s = {"images": [], "context": [], "ts": time.time()}
        _sessions[chat_id] = s
    return s


def process(message: dict) -> None:
    chat_id = str(message["chat"]["id"])

    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return

    text = message.get("text", "")

    if text.startswith("/reset"):
        _sessions.pop(chat_id, None)
        tg_send(chat_id, "Session cleared.")
        return

    if text.startswith("/status"):
        s = _session(chat_id)
        tg_send(chat_id, f"Session: {len(s['images'])} image(s), {len(s['context'])} context message(s).")
        return

    s = _session(chat_id)

    if "photo" in message:
        file_id = message["photo"][-1]["file_id"]
        s["images"].append(file_id)
        s["ts"] = time.time()
        tg_send(chat_id, f"Image received ({len(s['images'])} total in session).")
        return

    if text and not text.startswith("/"):
        s["context"].append(text)
        s["ts"] = time.time()
        tg_send(chat_id, "Context added.")
        return

    audio = message.get("voice") or message.get("audio") or message.get("document")
    if audio:
        session_id = f"{chat_id}-{message['message_id']}"
        base_path = f"uploads/{session_id}"

        tg_send(chat_id, "Audio received. Preparing ingest session…")

        context_text = "\n".join(s["context"]).strip()
        if context_text:
            gh_put_file(
                f"{base_path}/context.txt",
                context_text.encode(),
                f"ingest: context {session_id}",
            )

        for idx, image_id in enumerate(s["images"]):
            downloaded = tg_download(image_id)
            if not downloaded:
                continue
            img_blob, _ = downloaded
            gh_put_file(
                f"{base_path}/img_{idx}.jpg",
                img_blob,
                f"ingest: image {idx} {session_id}",
            )

        audio_blob = tg_download(audio["file_id"])
        if not audio_blob:
            tg_send(chat_id, "Audio download failed. Please try again.")
            return

        audio_bytes, audio_path = audio_blob
        ext = audio_path.rsplit(".", 1)[-1].lower() if "." in audio_path else "ogg"
        ok = gh_put_file(
            f"{base_path}/audio.{ext}",
            audio_bytes,
            f"ingest: audio trigger {session_id}",
        )

        if ok:
            log(f"Ingest staged: {session_id}")
            tg_send(chat_id, "Ingest staged. Processing started.")
            _sessions.pop(chat_id, None)
        else:
            tg_send(chat_id, "Failed to stage ingest session on GitHub.")


def main() -> None:
    log(f"Listener started. Max runtime: {MAX_RUNTIME}s. Repo: {GH_REPO} Branch: {INGEST_BRANCH}")
    deadline = time.time() + MAX_RUNTIME
    offset: int | None = None
    errors = 0

    while time.time() < deadline:
        try:
            updates = tg_get_updates(offset)
            errors = 0
        except Exception as exc:
            errors += 1
            log(f"getUpdates error ({errors}): {exc}")
            time.sleep(min(5 * errors, 60))
            continue

        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message")
            if not msg:
                continue
            try:
                process(msg)
            except Exception as exc:
                log(f"Error processing update {update['update_id']}: {exc}")

    log("Max runtime reached. Exiting for self-restart.")


if __name__ == "__main__":
    main()
