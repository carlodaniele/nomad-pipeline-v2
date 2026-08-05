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

## Setup Guide

The pipeline runs entirely on GitHub Actions — no server or hosting required. Follow these steps once to configure all required credentials.

---

### 1 — Fork or clone this repository

Fork this repository to your own GitHub account (or clone it and push to a new private repo). All configuration is done through GitHub repository secrets and variables, so the code itself never contains credentials.

---

### 2 — Create the Telegram bot (`TELEGRAM_BOT_TOKEN`)

1. Open Telegram and start a conversation with [@BotFather](https://t.me/BotFather).
2. Send the command `/newbot`.
3. When prompted, enter a **display name** for the bot (e.g. `My Content Pipeline`).
4. When prompted, enter a **username** — it must be unique and end in `bot` (e.g. `my_content_pipeline_bot`).
5. BotFather replies with a message containing your **bot token**, a string in the format:

   ```
   123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

6. Copy this token. This is the value for the `TELEGRAM_BOT_TOKEN` secret. Keep it private — anyone with this token can control your bot.

> **Bot privacy in groups:** By default, bots in group chats only receive messages that mention them directly. If you plan to use the bot in a group, you must disable this:
> 1. Send `/mybots` to BotFather.
> 2. Select your bot → **Bot Settings** → **Group Privacy** → **Turn off**.

---

### 3 — Find your authorized chat IDs (`TELEGRAM_ALLOWED_CHAT_IDS`)

The pipeline only processes messages from chat IDs you explicitly authorize. To find your chat ID:

1. Open Telegram and send **any message** to your new bot (e.g. "hello").
2. In a browser, open the following URL, replacing `<YOUR_TOKEN>` with your bot token:

   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```

3. The response is a JSON object. Find the `"chat"` key inside the latest update:

   ```json
   "chat": {
     "id": 123456789,
     "first_name": "Carlo",
     "type": "private"
   }
   ```

4. The `"id"` value is your chat ID. For group chats, the ID is negative (e.g. `-100123456789`).
5. Copy the numeric value. This is the value for `TELEGRAM_ALLOWED_CHAT_IDS`. To authorize multiple users or groups, separate their IDs with commas:

   ```
   123456789,-100987654321
   ```

> If `getUpdates` returns an empty `result` array, make sure you sent a message to the bot first, then refresh the page.

---

### 4 — Create a GitHub Personal Access Token (`GH_DISPATCH_TOKEN`)

GitHub Actions cannot trigger other workflow runs using its built-in token. You need a Personal Access Token (PAT) with the right permissions.

1. Go to [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens) and click **Generate new token** → **Fine-grained tokens**.
2. Set a **Token name** (e.g. `Nomad Pipeline v2 Dispatch`).
3. Set an **Expiration** (1 year recommended; remember to rotate it before it expires).
4. Under **Repository access**, select **Only selected repositories** and choose your pipeline repository.
5. Under **Permissions**, expand **Repository permissions** and set:
   - **Contents** → **Read and write**
   - **Actions** → **Read and write**
6. Click **Generate token** and copy the result immediately — GitHub shows it only once.

This is the value for the `GH_DISPATCH_TOKEN` secret. This token allows the listener to:
- Dispatch the `pipeline-run` workflow when audio is received.
- Restart itself automatically after the maximum runtime is reached.

---

### 5 — WordPress site URL and credentials (`WP_ABILITY_URL`, `WP_ABILITY_AUTH`)

These are required only when using the `wordpress` adapter.

#### `WP_ABILITY_URL`

This is the base URL of your WordPress site, without a trailing slash. Example:

```
https://yoursite.com
```

The pipeline appends the Ability endpoint path automatically.

#### `WP_ABILITY_AUTH`

WordPress uses **Application Passwords** for API authentication (available since WordPress 5.6).

1. Log in to your WordPress admin panel.
2. Go to **Users → Profile** (or **Users → All Users** → click your username).
3. Scroll down to the **Application Passwords** section.
4. In the **New Application Password Name** field, enter `Nomad Pipeline v2`.
5. Click **Add New Application Password**.
6. WordPress generates a password in this format (with spaces):

   ```
   xxxx xxxx xxxx xxxx xxxx xxxx
   ```

7. Copy it immediately — it is shown only once.
8. Combine your WordPress **username** and the application password into a single string, separated by a colon:

   ```
   your_username:xxxx xxxx xxxx xxxx xxxx xxxx
   ```

This combined string is the value for `WP_ABILITY_AUTH`. The spaces in the password are intentional and must be preserved.

> The user must have the `edit_posts` capability. An Administrator or Editor role is sufficient.

> The WordPress site must have the **Nomad Pipeline Audio to Draft** plugin installed and activated.

> **Note on AI costs:** transcription and content generation happen inside WordPress via the AI connector you configure in the plugin (Settings → AI Connector). You do not need a separate OpenAI API key for this pipeline.

---

### 7 — Add secrets and variables to GitHub

1. In your GitHub repository, go to **Settings → Secrets and variables → Actions**.

2. Under the **Secrets** tab, select **Repository secrets** and click **New repository secret** for each of the following:

   | Secret name                 | Value                                      |
   |-----------------------------|--------------------------------------------|
   | `TELEGRAM_BOT_TOKEN`        | Bot token from BotFather (step 2)          |
   | `TELEGRAM_ALLOWED_CHAT_IDS` | Comma-separated authorized chat IDs (step 3) |
   | `GH_DISPATCH_TOKEN`         | GitHub PAT (step 4)                        |
   | `WP_ABILITY_URL`            | WordPress site URL (step 5)                |
   | `WP_ABILITY_AUTH`           | WordPress username:app_password (step 5)   |

3. Under the **Variables** tab, select **Repository variables** and click **New repository variable** and add:

   | Variable name      | Value       |
   |--------------------|-------------|
   | `PIPELINE_ADAPTER` | `wordpress` |

---

### 8 — Start the listener

The Telegram listener runs as a long-polling GitHub Actions job. It stays active for up to 5.5 hours, then restarts itself automatically.

1. In your repository, go to **Actions → Telegram Listener**.
2. Click **Run workflow** → **Run workflow**.
3. The job starts within a few seconds. The bot is now active.

To verify the listener is running, send a message to your bot — you should receive an immediate acknowledgment.

> The listener also restarts automatically via a scheduled cron job every 6 hours as a safety net. You do not need to start it again manually after the first time unless you cancel it intentionally.

---

### Session flow reference

Each user session is identified by the Telegram `chat_id`. The pipeline buffers images and text messages per session until an audio message arrives.

```
[photo]   →  bot replies "Image received (N total)"
[text]    →  bot replies "Context added"
[audio]   →  bot replies "Processing started…"
              pipeline-run workflow is triggered
                 → audio downloaded from Telegram
                 → images uploaded to WordPress media library
                 → audio transcribed (OpenAI Whisper)
                 → draft post created via WordPress Ability
              bot replies "Done! Draft published: <url>"
              — or —
              bot replies "Failed: <reason>"
```

Sessions are stored in memory for the duration of the listener run. Sending `/reset` clears the current session. Sending `/status` reports how many images and context messages are buffered.

---

### Security notes

- Never commit any credential or token to the repository.
- `TELEGRAM_ALLOWED_CHAT_IDS` is the access control list. Only messages from listed chat IDs are processed; all others are silently ignored.
- Rotate `GH_DISPATCH_TOKEN` before its expiration date.
- Use a dedicated WordPress user for the API credentials rather than an administrator account if your site has multiple users.
