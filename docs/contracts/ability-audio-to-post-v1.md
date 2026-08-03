# Ability Contract v1 - audio-to-post

## Scope

Canonical request/response contract for Telegram-triggered audio-to-content runs.

## Input

Required fields:
- contract_version
- external_run_id
- source
- audio

Optional fields:
- source_metadata
- editorial_options
- proper_noun_hints
- publish_options
- media_options

## Output

Required fields:
- contract_version
- run_id
- status
- quality_flags
- processing_timestamps
- debug_reference_id

Conditional fields:
- post_id and post_url when status=completed
- error when status=failed
