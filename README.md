# Nomad Pipeline v2

Adapter-first, CMS-agnostic pipeline using a strict legacy-style runtime flow: one workflow starts only when an audio file arrives in `uploads/`.

## How it works

1. Files are staged directly into `uploads/` (images and optional `.txt` context files).
2. When `uploads/audio.<ext>` is pushed (`.oga`, `.mp3`, `.m4a`), the workflow starts automatically.
3. The workflow runs the selected adapter (WordPress by default): upload images, upload audio, build Ability input JSON, call Ability.
4. Session files are moved from `uploads/` to `processed/` (or `failed/` if an error occurs), then the job ends.

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

## Legacy-Style Ingest Mode (Single Runtime Workflow)

This mode uses one runtime workflow only. Processing starts only when an audio file is pushed in `uploads/` on branch `ingest`.

### 1 - Create and push ingest branch

```bash
git checkout -b ingest
git push -u origin ingest
git checkout main
```

### 2 - Add GitHub secrets

Required for processing workflow:

- `WP_ABILITY_URL`
- `WP_ABILITY_AUTH`

Required for adapter execution:

- `WP_ABILITY_URL`
- `WP_ABILITY_AUTH`

### 3 - Stage session files

Push images/text in `uploads/` first, then push the audio file in `uploads/`.

### 4 - Trigger behavior

- Images/text only: no processing run.
- Audio pushed under `uploads/*.oga|*.mp3|*.m4a`: processing starts automatically.
- Success: session moved to `processed/`.
- Failure: session moved to `failed/`.

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

### 4 — Trigger source

The workflow trigger is the Git push that introduces `uploads/*.oga`, `uploads/*.mp3`, or `uploads/*.m4a` on branch `ingest`.

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
   | `WP_ABILITY_URL`            | WordPress site URL (step 5)                |
   | `WP_ABILITY_AUTH`           | WordPress username:app_password (step 5)   |

3. Under the **Variables** tab, select **Repository variables** and click **New repository variable** and add:

   | Variable name      | Value       |
   |--------------------|-------------|
   | `PIPELINE_ADAPTER` | `wordpress` |
   | `INGEST_BRANCH`    | `ingest`    |

---

### 8 — Runtime workflow

`Nomad Pipeline Execution` starts automatically on audio file push under `uploads/*` on branch `ingest`.

---

### Session flow reference

The workflow reads files from `uploads/` root.

```
stage image(s) + optional .txt context in uploads/
stage audio as uploads/audio.<ext>
              push of audio file triggers Ingest Audio Pipeline
                 → images uploaded to WordPress media library
                 → audio uploaded to WordPress media library
                 → ability called with structured JSON input
              processed files moved to processed/ or failed/
```

---

### Security notes

- Never commit any credential or token to the repository.
- Keep `uploads/` as temporary staging only; do not use it as permanent storage.
- Use a dedicated WordPress user for the API credentials rather than an administrator account if your site has multiple users.
