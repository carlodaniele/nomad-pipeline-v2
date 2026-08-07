import os
import json
import base64
import mimetypes
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AudioInputMediaId(BaseModel):
    media_id: int

class PhotoInput(BaseModel):
    filename: str
    mime_type: str
    base64: str

class AbilityInputParams(BaseModel):
    contract_version: str = "1.0.0"
    external_run_id: str
    source: str = "api"
    audio: AudioInputMediaId
    photos: List[PhotoInput] = Field(default_factory=list)
    status: str = "draft"
    adapter: str = "wordpress"

class AbilityRequestPayload(BaseModel):
    input: AbilityInputParams

def encode_file_to_b64(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_audio_filepath(input_folder: str) -> Optional[str]:
    if not os.path.exists(input_folder):
        return None

    for filename in sorted(os.listdir(input_folder)):
        filepath = os.path.join(input_folder, filename)
        if not os.path.isfile(filepath) or filename.startswith("."):
            continue

        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or ""
        if mime_type.startswith("audio/") or filename.lower().endswith((".mp3", ".m4a", ".wav", ".ogg", ".oga")):
            return filepath

    return None

def build_payload_with_media_id(media_id: int) -> Dict[str, Any]:
    input_folder = os.getenv("GH_INPUT_FOLDER", "media-input")
    post_status = os.getenv("WP_POST_STATUS", "draft")
    adapter_name = os.getenv("NOMAD_PIPELINE_ADAPTER", "wordpress")

    gh_run_id = os.getenv("GITHUB_RUN_ID")
    gh_run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
    if gh_run_id:
        external_run_id = f"gh-{gh_run_id}-{gh_run_attempt}"
    else:
        external_run_id = f"local-{uuid.uuid4().hex[:12]}"

    photo_files: List[PhotoInput] = []

    if os.path.exists(input_folder):
        for filename in sorted(os.listdir(input_folder)):
            filepath = os.path.join(input_folder, filename)
            if not os.path.isfile(filepath) or filename.startswith("."):
                continue

            mime_type, _ = mimetypes.guess_type(filepath)
            mime_type = mime_type or "application/octet-stream"

            if mime_type.startswith("image/"):
                b64_data = encode_file_to_b64(filepath)
                photo_files.append(
                    PhotoInput(
                        filename=filename,
                        mime_type=mime_type,
                        base64=b64_data
                    )
                )

    params = AbilityInputParams(
        contract_version="1.0.0",
        external_run_id=external_run_id,
        source="api",
        audio=AudioInputMediaId(media_id=media_id),
        photos=photo_files,
        status=post_status,
        adapter=adapter_name
    )

    payload = AbilityRequestPayload(input=params)
    return payload.model_dump(exclude_none=True)

if __name__ == "__main__":
    dummy_payload = build_payload_with_media_id(330)
    print(json.dumps(dummy_payload, indent=2))