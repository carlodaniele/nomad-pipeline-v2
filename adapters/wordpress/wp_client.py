import os
import time
import mimetypes
import requests
from urllib.parse import urljoin, urlparse
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, List, Optional
from .payload_builder import build_payload_with_media_id, get_audio_filepath

def _normalize_base_url(value: str) -> str:
    base = (value or "").strip()
    if not base:
        raise ValueError("WP_URL/WP_BASE_URL non configurata nelle variabili d'ambiente.")

    parsed = urlparse(base)
    if not parsed.scheme:
        base = f"https://{base.lstrip('/')}"

    return base.rstrip("/")


def _normalize_endpoint(base_url: str, endpoint: str) -> str:
    raw = (endpoint or "").strip()
    if not raw:
        raise ValueError("NOMAD_PIPELINE_WP_ABILITY_ENDPOINT non configurato.")

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        return raw

    return urljoin(f"{base_url}/", raw.lstrip("/"))


def _resolve_wp_credentials() -> tuple[str, str]:
    username = (os.getenv("WP_USERNAME", "") or "").strip()
    app_password = (os.getenv("WP_APP_PASSWORD", "") or "")

    # Backward compatibility with legacy combined auth env var.
    combined = (os.getenv("WP_ABILITY_AUTH", "") or "").strip()
    if (not username or not app_password) and combined:
        if ":" in combined:
            user_part, pass_part = combined.split(":", 1)
        elif "|" in combined:
            user_part, pass_part = combined.split("|", 1)
        else:
            raise ValueError(
                "WP_ABILITY_AUTH non valido: usa formato 'username:application_password'."
            )
        username = username or user_part.strip()
        app_password = app_password or pass_part

    if not username or not app_password:
        raise ValueError(
            "Credenziali WP mancanti: configura WP_USERNAME+WP_APP_PASSWORD oppure WP_ABILITY_AUTH."
        )

    return username, app_password


WP_URL = _normalize_base_url(
    os.getenv("WP_URL")
    or os.getenv("WP_BASE_URL")
    or os.getenv("WP_ABILITY_URL")
    or "https://audioconverter.kinsta.cloud"
)
WP_USERNAME, WP_APP_PASSWORD = _resolve_wp_credentials()

ABILITY_ENDPOINT = _normalize_endpoint(
    WP_URL,
    os.getenv(
        "NOMAD_PIPELINE_WP_ABILITY_ENDPOINT",
        "/wp-json/wp-abilities/v1/abilities/nomad-pipeline-audio-to-draft/audio-to-post/run",
    ),
)
MEDIA_ENDPOINT = f"{WP_URL}/wp-json/wp/v2/media"
POSTS_ENDPOINT = f"{WP_URL}/wp-json/wp/v2/posts"

def upload_file_to_wordpress(filepath: str) -> Dict[str, Any]:
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
    media_url = media_data.get("source_url")
    print(f"[Pipeline] File uploaded successfully. Media ID: {media_id}")
    return {"id": media_id, "url": media_url}

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

def build_media_blocks(images: List[Dict[str, Any]]) -> str:
    """
    Genera il markup dei blocchi Gutenberg (wp:image singolo o wp:gallery)
    a partire da id/url delle immagini gia' caricate. Questo e' puro markup
    locale: gli id delle immagini non vengono mai inviati all'Ability.
    """
    images = [img for img in images if img.get("id") and img.get("url")]
    if not images:
        return ""

    if len(images) == 1:
        img = images[0]
        return (
            f'\n\n<!-- wp:image {{"id":{img["id"]},"sizeSlug":"large","linkDestination":"none"}} -->\n'
            f'<figure class="wp-block-image size-large">'
            f'<img src="{img["url"]}" class="wp-image-{img["id"]}"/></figure>\n'
            f'<!-- /wp:image -->\n'
        )

    blocks = '\n\n<!-- wp:gallery {"linkTo":"none"} -->\n'
    blocks += '<figure class="wp-block-gallery has-nested-images columns-default is-cropped">\n'
    for img in images:
        blocks += (
            f'<!-- wp:image {{"id":{img["id"]},"sizeSlug":"large","linkDestination":"none"}} -->\n'
            f'<figure class="wp-block-image size-large">'
            f'<img src="{img["url"]}" class="wp-image-{img["id"]}"/></figure>\n'
            f'<!-- /wp:image -->\n'
        )
    blocks += '</figure>\n<!-- /wp:gallery -->\n'
    return blocks

def get_post_raw_content(post_id: int) -> str:
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    url = f"{POSTS_ENDPOINT}/{post_id}"
    # context=edit e' necessario per ricevere content.raw invece del solo rendered.
    response = requests.get(url, params={"context": "edit"}, auth=auth, timeout=60)
    response.raise_for_status()
    content = response.json().get("content", {})
    if isinstance(content, dict):
        return content.get("raw") or content.get("rendered") or ""
    return content or ""

def append_media_blocks_to_post(post_id: int, images: List[Dict[str, Any]]) -> None:
    blocks = build_media_blocks(images)
    if not blocks:
        return

    current_content = get_post_raw_content(post_id)
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    url = f"{POSTS_ENDPOINT}/{post_id}"
    response = requests.post(
        url,
        json={"content": current_content + blocks},
        auth=auth,
        timeout=60
    )
    if response.ok:
        print(f"[Pipeline] Blocchi immagine/galleria aggiunti al post {post_id}.")
    else:
        print(f"[Pipeline] Errore aggiunta blocchi immagine: {response.status_code} {response.text}")

def run_pipeline() -> Dict[str, Any]:
    input_folder = os.getenv("GH_INPUT_FOLDER", "media-input")
    
    audio_path = get_audio_filepath(input_folder)
    if not audio_path:
        raise FileNotFoundError(f"No audio file found in folder '{input_folder}'.")

    image_paths = get_image_filepaths(input_folder)

    # 1. Upload audio
    audio_media = upload_file_to_wordpress(audio_path)
    audio_media_id = audio_media["id"]

    # 2. Upload preventivo delle immagini (id + url, servono solo per generare i blocchi)
    uploaded_images = []
    for img_path in image_paths:
        uploaded_images.append(upload_file_to_wordpress(img_path))

    # 3. Esecuzione Ability per generare la bozza del post.
    # Il payload contiene SOLO l'audio: l'Ability non accetta image_media_ids.
    payload = build_payload_with_media_id(audio_media_id)
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)

    # Retry su ai_provider_unavailable: errore transitorio del provider di trascrizione.
    _ability_max_attempts = 3
    _ability_retry_delay = 10
    result = None
    for attempt in range(1, _ability_max_attempts + 1):
        print(f"[Pipeline] Sending POST request to Ability endpoint (attempt {attempt}/{_ability_max_attempts})...")
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

        if result.get("status") == "failed":
            error_info = result.get("error", {})
            err_code = error_info.get("code", "unknown_error")
            err_msg = error_info.get("message", "No details provided")
            if err_code == "ai_provider_unavailable" and attempt < _ability_max_attempts:
                print(f"[Pipeline] AI provider unavailable, retry in {_ability_retry_delay}s...")
                time.sleep(_ability_retry_delay)
                continue
            print(f"[Pipeline] Ability execution failed: [{err_code}] {err_msg}")
            raise RuntimeError(f"Ability execution failed: [{err_code}] {err_msg}")

        break

    print("[Pipeline] Ability executed successfully.")
    post_id = result.get("post_id")

    # 4. Le immagini vengono gestite interamente lato pipeline:
    #    - associate come allegati del post
    #    - la prima impostata come immagine in evidenza
    #    - i blocchi wp:image / wp:gallery generati qui e aggiunti al content
    if post_id and uploaded_images:
        print(f"[Pipeline] Attaching {len(uploaded_images)} images to post {post_id}...")
        for idx, img in enumerate(uploaded_images):
            attach_image_to_post(img["id"], post_id)
            if idx == 0:
                set_featured_image(post_id, img["id"])

        append_media_blocks_to_post(post_id, uploaded_images)

    return result

if __name__ == "__main__":
    result = run_pipeline()
    print(result)