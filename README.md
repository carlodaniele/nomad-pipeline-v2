# Nomad Pipeline v2

CMS-agnostic pipeline (WordPress Ability adapter) using a single runtime workflow: processing starts only when an audio file arrives in `media-input/` on branch `main`.

## How it works

1. Files are staged into `media-input/` (images and one audio file per session), either manually via `git push` or automatically via the Telegram ingest workflow described below.
2. When an audio file matching `media-input/*.oga|*.ogg|*.mp3|*.m4a|*.wav|*.webm` is pushed to `main`, the `Nomad Pipeline v2 Execution` workflow starts automatically.
3. The workflow (`wp_client.py`): uploads the audio and any images to the WordPress Media Library, builds the Ability input JSON (`payload_builder.py`), and calls the WordPress Ability endpoint to generate the post.
4. On success, `media-input/` is emptied (cleanup step) so the folder is ready for the next session.

## Repository structure

```
telegram_poll.py          Polls Telegram for new files and stages them into media-input/
wp_client.py               Uploads media to WordPress and calls the Ability endpoint
payload_builder.py         Builds the Ability request payload
media-input/                Staging folder — temporary only, do not use as permanent storage
.github/workflows/
  pipeline.yml              Runs on push of an audio file to media-input/ (branch main)
  telegram-poll.yml          Scheduled polling job that feeds media-input/ from Telegram
```

## Getting files into `media-input/`

There are two ways to stage a session:

- **Manual:** `git push` the image(s) first, then the audio file, directly into `media-input/` on `main`.
- **Automatic (Telegram):** send the audio (and optional images) to your Telegram bot. The `Telegram Ingest Polling` workflow (`telegram-poll.yml`) runs every 5 minutes (or on demand via "Run workflow"), downloads any new files from authorized chats, and commits them into `media-input/`, which then triggers `pipeline.yml`.

  This uses Telegram's `getUpdates` polling, not a real webhook — GitHub Actions has no always-on server to receive one. If `getUpdates` starts failing with a `409 Conflict`, it means an old webhook (e.g. from the legacy v1 project) is still registered; the polling script detects and removes it automatically on each run.

### Trigger behavior

- Images only: no processing run.
- Audio pushed under `media-input/*.oga|*.mp3|*.m4a|...`: processing starts automatically.
- Success: `media-input/` is cleared, ready for the next session.

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

The workflow trigger is the Git push that introduces `media-input/*.oga`, `*.ogg`, `*.mp3`, `*.m4a`, `*.wav`, or `*.webm` on branch `main`. Files can reach `media-input/` via a manual `git push` or automatically through the `Telegram Ingest Polling` workflow (see "Getting files into `media-input/`" above).

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

   | Secret name          | Value                                                                 |
   |-----------------------|------------------------------------------------------------------------|
   | `WP_USERNAME`         | WordPress username (step 5)                                            |
   | `WP_APP_PASSWORD`     | WordPress Application Password (step 5)                                |
   | `WP_ABILITY_AUTH`     | Alternative to the two above: `username:application_password` combined |
   | `TELEGRAM_BOT_TOKEN`  | Bot token from BotFather (step 2)                                      |
   | `GH_DISPATCH_TOKEN`   | A Personal Access Token with `repo` scope. **Required** — pushes made with the default `GITHUB_TOKEN` do not trigger other workflows, so both `pipeline.yml` and `telegram-poll.yml` need a real PAT here to chain correctly. |

3. Under the **Variables** tab, select **Repository variables** and click **New repository variable** and add:

   | Variable name                        | Value                                                                          |
   |----------------------------------------|-----------------------------------------------------------------------------------|
   | `WP_URL`                                | WordPress site URL (step 5)                                                      |
   | `WP_ABILITY_URL`                        | Same as `WP_URL` (kept for backward compatibility)                               |
   | `NOMAD_PIPELINE_WP_ABILITY_ENDPOINT`    | Ability endpoint path/URL — defaults to `/wp-json/wp-abilities/v1/abilities/nomad-pipeline-audio-to-draft/audio-to-post/run` if unset |
   | `NOMAD_PIPELINE_ADAPTER`                | `wordpress`                                                                       |
   | `WP_POST_STATUS`                        | e.g. `draft` or `publish`                                                        |
   | `GH_INPUT_FOLDER`                       | `media-input`                                                                     |
   | `TELEGRAM_ALLOWED_CHAT_IDS`             | Authorized chat IDs (step 3), comma-separated                                    |

---

### 8 — Runtime workflows

- `Nomad Pipeline v2 Execution` (`pipeline.yml`) starts automatically on audio file push under `media-input/*` on branch `main`.
- `Telegram Ingest Polling` (`telegram-poll.yml`) runs on a 5-minute schedule (and on demand) to pull new files from Telegram into `media-input/`.

---

### Session flow reference

```
send image(s) + audio to the Telegram bot
              Telegram Ingest Polling downloads them into media-input/
              push of an audio file triggers Nomad Pipeline v2 Execution
                 → images uploaded to WordPress media library
                 → audio uploaded to WordPress media library
                 → Ability called with structured JSON input
              media-input/ cleared on success
```

Manual staging (`git push` directly into `media-input/` on `main`) works the same way, without the Telegram step.

---

### Security notes

- Never commit any credential or token to the repository.
- Keep `media-input/` as temporary staging only; do not use it as permanent storage.
- Use a dedicated WordPress user for the API credentials rather than an administrator account if your site has multiple users.
- `TELEGRAM_ALLOWED_CHAT_IDS` is the only access control on the Telegram ingest path — keep it accurate and keep `TELEGRAM_BOT_TOKEN` private.
