import os
import requests
from typing import Dict, Any, Optional
from payload_builder import build_payload_with_media_id, get_audio_filepath

WP_BASE_URL = os.getenv("WP_BASE_URL", "https://audioconverter.kinsta.cloud")
WP_APPLICATION_PASSWORD = os.getenv("WP_APPLICATION_PASSWORD", "")
WP_USERNAME = os.getenv("WP_USERNAME", "")

ABILITY_ENDPOINT = f"{WP_BASE_URL}/wp-json/wp-abilities/v1/abilities/nomad-pipeline-audio-to-draft/audio-to-post/run"
MEDIA_ENDPOINT = f"{WP_BASE_URL}/wp-json/wp/v2/media"

def upload_audio_to_wordpress(filepath: str) -> int:
    filename = os.path.basename(filepath)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "audio/mpeg",
    }

    auth = (WP_USERNAME, WP_APPLICATION_PASSWORD) if WP_USERNAME and WP_APPLICATION_PASSWORD else None

    print(f"[Pipeline] Uploading audio file '{filename}' to WordPress Media Library...")
    with open(filepath, "rb") as audio_file:
        response = requests.post(
            MEDIA_ENDPOINT,
            headers=headers,
            data=audio_file,
            auth=auth,
            timeout=120
        )

    response.raise_for_status()
    media_data = response.json()
    media_id = media_data.get("id")
    print(f"[Pipeline] Audio uploaded successfully. Media ID: {media_id}")
    return media_id

def run_pipeline() -> Dict[str, Any]:
    input_folder = os.getenv("GH_INPUT_FOLDER", "media-input")
    audio_path = get_audio_filepath(input_folder)

    if not audio_path:
        raise FileNotFoundError(f"No audio file found in folder '{input_folder}'.")

    media_id = upload_audio_to_wordpress(audio_path)
    payload = build_payload_with_media_id(media_id)

    auth = (WP_USERNAME, WP_APPLICATION_PASSWORD) if WP_USERNAME and WP_APPLICATION_PASSWORD else None
    
    print(f"[Pipeline] Sending POST request to Ability endpoint...")
    response = requests.post(
        ABILITY_ENDPOINT,
        json=payload,
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=180
    )

    response.raise_for_status()
    print("[Pipeline] Ability executed successfully.")
    return response.json()

if __name__ == "__main__":
    result = run_pipeline()
    print(result)