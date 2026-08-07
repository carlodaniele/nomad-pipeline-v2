import os
import json
import mimetypes
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AudioInputMediaId(BaseModel):
    media_id: int

class AbilityInputParams(BaseModel):
    contract_version: str = "1.0.0"
    external_run_id: str
    source: str = "api"
    audio: AudioInputMediaId
    status: str = "draft"
    adapter: str = "wordpress"

class AbilityRequestPayload(BaseModel):
    input: AbilityInputParams

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
    post_status = os.getenv("WP_POST_STATUS", "draft")
    adapter_name = os.getenv("NOMAD_PIPELINE_ADAPTER", "wordpress")

    gh_run_id = os.getenv("GITHUB_RUN_ID")
    gh_run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
    if gh_run_id:
        external_run_id = f"gh-{gh_run_id}-{gh_run_attempt}"
    else:
        external_run_id = f"local-{uuid.uuid4().hex[:12]}"

    params = AbilityInputParams(
        contract_version="1.0.0",
        external_run_id=external_run_id,
        source="api",
        audio=AudioInputMediaId(media_id=media_id),
        status=post_status,
        adapter=adapter_name
    )

    payload = AbilityRequestPayload(input=params)
    return payload.model_dump(exclude_none=True)

if __name__ == "__main__":
    dummy_payload = build_payload_with_media_id(330)
    print(json.dumps(dummy_payload, indent=2))