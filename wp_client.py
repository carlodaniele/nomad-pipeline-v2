import os
import mimetypes
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, List, Optional
from payload_builder import build_payload_with_media_id, get_audio_filepath

WP_BASE_URL = os.getenv("WP_BASE_URL", "https://audioconverter.kinsta.cloud")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

ABILITY_ENDPOINT = f"{WP_BASE_URL}/wp-json/wp-abilities/v1/abilities/nomad-pipeline-audio-to-draft/audio-to-post/run"
MEDIA_ENDPOINT = f"{WP_BASE_URL}/wp-json/wp/v2/media"
POSTS_ENDPOINT = f"{WP_BASE_URL}/wp-json/wp/v2/posts"

def upload_file_to_wordpress(filepath: str) -> int:
    filename = os.path.basename(filepath)
    mime_type, _ = mimetypes.guess_type(filepath)
    
    if not mime_type:
        if filename.lower().endswith('.oga'):
            mime_type = 'audio/ogg'
        else:
            mime_type = 'application/octet-stream'

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": mime_type,
    }

    if not WP_USERNAME or not WP_APP_PASSWORD:
        raise ValueError("WP_USERNAME o WP_APP_PASSWORD non configurati nelle variabili d'ambiente.")

    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)

    print(f"[Pipeline] Uploading '{filename}' ({mime_type}) to WordPress Media Library...")
    with open(filepath, "rb") as media_file:
        response = requests.post(
            MEDIA_ENDPOINT,
            headers=headers,
            data=media_file,
            auth=auth,
            timeout=120
        )

    if response.status_code not in (200, 201):
        print(f"[Pipeline] Upload Failed. Response Body: {response.text}")

    response.raise_for_status()
    media_data = response.json()
    media_id = media_data.get("id")
    print(f"[Pipeline] File uploaded successfully. Media ID: {media_id}")
    return media_id

def get_image_filepaths(input_folder: str) -> List[str]:
    images = []
    if not os.path.exists(input_folder):
        return images

    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    for filename in sorted(os.listdir(input_folder)):
        filepath = os.path.join(input_folder, filename)
        if not os.path.isfile(filepath) or filename.startswith("."):
            continue

        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or ""
        if mime_type.startswith("image/") or filename.lower().endswith(valid_extensions):
            images.append(filepath)

    return images

def attach_image_to_post(media_id: int, post_id: int) -> None:
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    url = f"{MEDIA_ENDPOINT}/{media_id}"
    response = requests.post(url, json={"post": post_id}, auth=auth, timeout=60)
    if response.ok:
        print(f"[Pipeline] Media {media_id} attached to Post {post_id}.")

def set_featured_image(post_id: int, media_id: int) -> None:
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    url = f"{POSTS_ENDPOINT}/{post_id}"
    response = requests.post(url, json={"featured_media": media_id}, auth=auth, timeout=60)
    if response.ok:
        print(f"[Pipeline] Set Media {media_id} as featured image for Post {post_id}.")

def run_pipeline() -> Dict[str, Any]:
    input_folder = os.getenv("GH_INPUT_FOLDER", "media-input")
    
    audio_path = get_audio_filepath(input_folder)
    if not audio_path:
        raise FileNotFoundError(f"No audio file found in folder '{input_folder}'.")

    image_paths = get_image_filepaths(input_folder)

    # 1. Upload audio
    audio_media_id = upload_file_to_wordpress(audio_path)

    # 2. Upload preventive delle immagini
    uploaded_image_ids = []
    for img_path in image_paths:
        img_id = upload_file_to_wordpress(img_path)
        uploaded_image_ids.append(img_id)

    # 3. Esecuzione Ability per generare la bozza del post
    payload = build_payload_with_media_id(audio_media_id)
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)

    print("[Pipeline] Sending POST request to Ability endpoint...")
    response = requests.post(
        ABILITY_ENDPOINT,
        json=payload,
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=180
    )

    if not response.ok:
        print(f"[Pipeline] Ability Failed. Response Body: {response.text}")

    response.raise_for_status()
    result = response.json()
    print("[Pipeline] Ability executed successfully.")

    post_id = result.get("post_id")

    # 4. Associazione delle immagini al post e impostazione dell'immagine in evidenza
    if post_id and uploaded_image_ids:
        print(f"[Pipeline] Attaching {len(uploaded_image_ids)} images to post {post_id}...")
        for idx, img_id in enumerate(uploaded_image_ids):
            attach_image_to_post(img_id, post_id)
            if idx == 0:
                set_featured_image(post_id, img_id)

    return result

if __name__ == "__main__":
    result = run_pipeline()
    print(result)