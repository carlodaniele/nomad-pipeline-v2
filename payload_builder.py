import os
import json
import base64
import mimetypes
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class MediaFile(BaseModel):
    filename: str
    mime_type: str
    content_b64: str
    content: str

class AbilityInputParams(BaseModel):
    contract_version: str = "1.0.0"
    external_run_id: str
    source: str = "api"
    audio: Optional[MediaFile] = None
    images: List[MediaFile] = []
    status: str = "draft"
    adapter: str = "wordpress"

class AbilityRequestPayload(BaseModel):
    input: AbilityInputParams

def encode_file_to_b64(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_payload() -> Dict[str, Any]:
    input_folder = os.getenv("GH_INPUT_FOLDER", "media-input")
    post_status = os.getenv("WP_POST_STATUS", "draft")
    adapter_name = os.getenv("NOMAD_PIPELINE_ADAPTER", "wordpress")

    gh_run_id = os.getenv("GITHUB_RUN_ID")
    gh_run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
    if gh_run_id:
        external_run_id = f"gh-{gh_run_id}-{gh_run_attempt}"
    else:
        external_run_id = f"local-{uuid.uuid4().hex[:12]}"

    audio_obj: Optional[MediaFile] = None
    image_files: List[MediaFile] = []

    if os.path.exists(input_folder):
        for filename in sorted(os.listdir(input_folder)):
            filepath = os.path.join(input_folder, filename)
            if not os.path.isfile(filepath) or filename.startswith("."):
                continue

            mime_type, _ = mimetypes.guess_type(filepath)
            mime_type = mime_type or "application/octet-stream"
            b64_data = encode_file_to_b64(filepath)

            media_item = MediaFile(
                filename=filename,
                mime_type=mime_type,
                content_b64=b64_data,
                content=b64_data
            )

            if mime_type.startswith("audio/") and audio_obj is None:
                audio_obj = media_item
            elif mime_type.startswith("image/"):
                image_files.append(media_item)

    params = AbilityInputParams(
        contract_version="1.0.0",
        external_run_id=external_run_id,
        source="api",
        audio=audio_obj,
        images=image_files,
        status=post_status,
        adapter=adapter_name
    )

    payload = AbilityRequestPayload(input=params)
    
    # Rimuove valori None dal dizionario generato
    return payload.model_dump(exclude_none=True)

if __name__ == "__main__":
    data = build_payload()
    print(json.dumps(data, indent=2))