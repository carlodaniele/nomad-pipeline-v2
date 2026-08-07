import os
import json
import requests
from requests.auth import HTTPBasicAuth
from payload_builder import build_payload

def send_telegram_notification(message: str) -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids_str = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
    
    if not bot_token or not chat_ids_str:
        print("[Telegram] Token o Chat IDs non configurati. Notifica saltata.")
        return

    chat_ids = [c.strip() for c in chat_ids_str.split(",") if c.strip()]
    
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code != 200:
                print(f"[Telegram] Errore invio a {chat_id}: {response.text}")
        except Exception as e:
            print(f"[Telegram] Eccezione invio notifica: {e}")

def run_pipeline():
    wp_url = os.getenv("WP_URL", "").strip("/")
    endpoint = os.getenv("NOMAD_PIPELINE_WP_ABILITY_ENDPOINT", "").strip("/")
    username = os.getenv("WP_USERNAME")
    password = os.getenv("WP_APP_PASSWORD")

    if not wp_url or not endpoint or not username or not password:
        error_msg = "❌ *Nomad Pipeline Error*\nConfigurazione WP non completa nei secrets/variables."
        print(error_msg)
        send_telegram_notification(error_msg)
        raise ValueError("Mancano parametri di configurazione WP obbligatori.")

    full_url = f"{wp_url}/{endpoint}"
    
    print("[Pipeline] Costruzione payload...")
    payload = build_payload()

    print(f"[Pipeline] Invio richiesta POST a: {full_url}")
    
    try:
        response = requests.post(
            full_url,
            json=payload,
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        if response.status_code in [200, 201]:
            res_data = response.json()
            success_msg = f"✅ *Nomad Pipeline Success*\nPost elaborato con successo!\n\n`Risposta`: {json.dumps(res_data, indent=2)[:500]}"
            print(success_msg)
            send_telegram_notification(success_msg)
        else:
            error_msg = f"⚠️ *Nomad Pipeline Failed*\nHTTP {response.status_code}\n\n`Risposta`: {response.text[:500]}"
            print(error_msg)
            send_telegram_notification(error_msg)
            response.raise_for_status()

    except Exception as e:
        msg = f"💥 *Nomad Pipeline Exception*\nErrore durante l'esecuzione: `{str(e)}`"
        print(msg)
        send_telegram_notification(msg)
        raise e

if __name__ == "__main__":
    run_pipeline()