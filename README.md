# Nomad Pipeline v2

Adapter-first, CMS-agnostic pipeline that converts Telegram audio, optional images, and optional context text into AI-generated, publish-ready content.

## How it works

1. The user sends optional images to the Telegram bot. Each image is acknowledged and buffered for the current session.
2. The user sends optional text messages providing context for the AI prompt. Each message is acknowledged and buffered.
3. The user sends an audio message. This triggers a GitHub Actions run.
4. The pipeline downloads the audio, transcribes it via AI, uploads the buffered images to the target CMS adapter to obtain media IDs, generates structured content using the transcript and text context, and publishes a draft via the configured adapter.
5. The bot sends the user a confirmation message with the published post URL, or a clear error message if the run failed.

## Goals

- Keep orchestration logic in `core/`.
- Keep CMS integrations in `adapters/`.
- Enforce a shared contract in `docs/contracts/`.
- Automate structure and contract checks in GitHub Actions.

## Repository structure

```
core/                     Platform-agnostic orchestration logic
adapters/
  wordpress/              WordPress Ability adapter
  astro/                  Astro publishing adapter
docs/contracts/           Versioned JSON schemas and examples
scripts/
  ci/                     Local validation scripts
  pipeline/               Pipeline execution scripts
.github/workflows/        CI automation
```

## Quick Start

```bash
bash scripts/ci/validate-structure.sh
bash scripts/ci/validate-contract.sh
bash scripts/pipeline/dry-run.sh
```

## Telegram Bot Setup

This pipeline is driven by a Telegram bot acting as the user-facing input interface. The bot must accept images, text messages, and audio files from authorized users.

### Step 1 — Create the bot

1. Open Telegram and start a conversation with [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts: choose a display name and a unique username ending in `bot`.
3. BotFather will return a **bot token** in the format `123456789:AAF...`. Save it securely — this is the value for the `TELEGRAM_BOT_TOKEN` secret.

### Step 2 — Get your chat ID

The pipeline must restrict processing to authorized senders. You need the numeric chat ID of every authorized user or group.

1. Start a conversation with your new bot (send any message).
2. Open a browser and visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
3. In the JSON response, look for `"chat": { "id": ... }`. The numeric value is your chat ID.
4. Save it as `TELEGRAM_ALLOWED_CHAT_IDS` (comma-separated if multiple).

### Step 3 — Configure bot privacy settings

By default Telegram bots in groups only receive messages that mention them. For this pipeline to receive all messages in a group chat:

1. In BotFather, send `/mybots` and select your bot.
2. Go to **Bot Settings → Group Privacy** and set it to **Disabled**.
   This allows the bot to receive all messages in groups it belongs to.

For private (one-to-one) conversations no change is needed.

### Step 4 — Configure file handling

The bot must be able to receive photos and audio files. No additional BotFather configuration is required — Telegram bots receive all file types by default. Ensure your webhook or polling handler processes the following update types:

| Update field   | Content                                         |
|----------------|-------------------------------------------------|
| `photo`        | Images sent by the user (pipeline buffers these) |
| `voice`        | Inline audio recordings (OGG/Opus)               |
| `audio`        | Uploaded audio files (MP3, M4A, WAV, etc.)       |
| `document`     | Files sent as documents (alternative for audio)  |
| `text`         | Plain text context messages                      |

### Step 5 — Set the webhook (GitHub Actions trigger)

Instead of running a persistent bot server, this pipeline uses a lightweight webhook that dispatches a GitHub Actions workflow on every relevant event.

1. Deploy a minimal webhook receiver (see `adapters/` for reference implementations) or use a serverless function.
2. Register the webhook with Telegram:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-webhook-endpoint/telegram"}'
   ```
3. Verify the webhook is active:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"
   ```
   The response should show `"url"` set and `"pending_update_count": 0`.

### Step 6 — GitHub repository secrets

Add the following secrets to your GitHub repository (**Settings → Secrets and variables → Actions**):

| Secret name                  | Description                                                    |
|------------------------------|----------------------------------------------------------------|
| `TELEGRAM_BOT_TOKEN`         | The bot token from BotFather                                   |
| `TELEGRAM_ALLOWED_CHAT_IDS`  | Comma-separated list of authorized numeric chat IDs            |
| `OPENAI_API_KEY`             | OpenAI API key for transcription and content generation        |
| `WP_ABILITY_URL`             | WordPress site URL for the Ability endpoint (WP adapter only)  |
| `WP_ABILITY_AUTH`            | WordPress application password or JWT token (WP adapter only)  |

### Step 7 — Session flow reference

Each user session is identified by the Telegram `chat_id`. The pipeline buffers images and text messages per session until an audio message arrives:

```
[image message]  →  ack "Image received (N total)"
[text message]   →  ack "Context added"
[audio message]  →  ack "Processing started…"
                     trigger GitHub Actions run
                     → transcribe audio
                     → upload images to CMS adapter
                     → generate content (transcript + context)
                     → publish draft
                 →  ack "Done — <post_url>" or "Failed — <reason>"
```

Each step sends an acknowledgment back to the user. A failed run always indicates whether it is retryable.

### Security notes

- Never commit `TELEGRAM_BOT_TOKEN` or any credential to the repository.
- Validate `chat_id` against `TELEGRAM_ALLOWED_CHAT_IDS` on every incoming update before any processing.
- Reject unknown senders silently (do not expose bot behavior to unauthorized callers).
