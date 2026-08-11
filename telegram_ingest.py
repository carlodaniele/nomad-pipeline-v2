import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_IDS = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
INPUT_FOLDER = os.getenv("GH_INPUT_FOLDER", "media-input")

os.makedirs(INPUT_FOLDER, exist_ok=True)

def fetch_telegram_media():
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram Ingest] TELEGRAM_BOT_TOKEN non configurato.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    if not response.ok:
        print(f"[Telegram Ingest] Errore getUpdates: {response.text}")
        return

    data = response.json()
    for update in data.get("result", []):
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))

        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            continue

        file_id = None
        file_name = ""

        if "voice" in message:
            file_id = message["voice"]["file_id"]
            file_name = f"audio_{message['message_id']}.oga"
        elif "audio" in message:
            file_id = message["audio"]["file_id"]
            ext = message["audio"].get("file_name", "audio.mp3").split(".")[-1]
            file_name = f"audio_{message['message_id']}.{ext}"
        elif "photo" in message:
            file_id = message["photo"][-1]["file_id"]  # Risoluzione massima
            file_name = f"photo_{message['message_id']}.jpg"

        if file_id:
            # Recupera path del file
            f_res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}").json()
            if f_res.get("ok"):
                file_path = f_res["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                
                # Scarica e salva in media-input/
                media_bytes = requests.get(download_url).content
                save_path = os.path.join(INPUT_FOLDER, file_name)
                with open(save_path, "wb") as f:
                    f.write(media_bytes)
                print(f"[Telegram Ingest] Scaricato: {file_name}")

if __name__ == "__main__":
    fetch_telegram_media()