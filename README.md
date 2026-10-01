# Nomad Pipeline v2

CMS-agnostic pipeline (WordPress and Astro adapters) using a single runtime workflow: processing starts only when an audio file arrives in `media-input/` on branch `main`.

## How it works

1. Files are staged into `media-input/` (images and one audio file per session), either manually via `git push` or automatically via the Telegram ingest workflow described below.
2. When an audio file matching `media-input/*.oga|*.ogg|*.mp3|*.m4a|*.wav|*.webm` is pushed to `main`, the `Nomad Pipeline v2 Execution` workflow starts automatically.
3. `nomad_pipeline.py` reads `NOMAD_PIPELINE_ADAPTER` and delegates to the selected adapter:
   - `wordpress`: uploads the audio and any images to the WordPress Media Library, builds the Ability input JSON, and calls the WordPress Ability endpoint — transcription and content generation happen inside WordPress.
   - `astro`: calls the shared AI engine (`core/ai_engine/`, Gemini by default) directly to transcribe the audio and generate the post, then writes a Markdown file (plus any images) into the Astro content collection.
4. On success, `media-input/` is emptied (cleanup step) so the folder is ready for the next session.

## Repository structure

```
telegram_poll.py            Polls Telegram for new files and stages them into media-input/
nomad_pipeline.py           Orchestrator — picks the adapter via NOMAD_PIPELINE_ADAPTER
core/ai_engine/             CMS-agnostic AI provider abstraction (used by non-WordPress adapters)
  base.py                    AIProvider interface + ContentResult contract
  content_generator.py       Provider factory, selected via AI_PROVIDER
  gemini_client.py           Gemini implementation (transcription + content generation)
  prompts.py                 Shared prompt template
adapters/wordpress/         Uploads media to WordPress and calls the Ability endpoint
adapters/astro/             Generates a Markdown post via core/ai_engine and writes it to the content collection
media-input/                Staging folder — temporary only, do not use as permanent storage
.github/workflows/
  pipeline.yml              Runs on push of an audio file to media-input/ (branch main)
   telegram-poll.yml          Dispatched polling job that feeds media-input/ from Telegram
```

## Getting files into `media-input/`

There are two ways to stage a session:

- **Manual:** `git push` the image(s) first, then the audio file, directly into `media-input/` on `main`.
- **Automatic (Telegram):** send the audio (and optional images) to your Telegram bot. A Kinsta cron dispatches `Telegram Ingest Polling` (`telegram-poll.yml`) every 5 minutes (or it can be run on demand). GitHub Actions downloads new files from authorized chats, snapshots `JOURNEY_ID` into an audio-sidecar `.json` file, and commits them into `media-input/`, which then triggers `pipeline.yml`.

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

### 6 — Astro adapter configuration (`GEMINI_API_KEY`, `ASTRO_CONTENT_DIR`, `ASTRO_ASSETS_DIR`)

These are required only when using the `astro` adapter. Unlike WordPress, Astro is a static site generator with no built-in AI backend, so the pipeline calls an AI provider directly via `core/ai_engine/`.

| Variable | Kind | Description |
|---|---|---|
| `NOMAD_PIPELINE_ADAPTER` | variable | Set to `astro` |
| `AI_PROVIDER` | variable | AI provider used by the ai_engine (default: `gemini`) |
| `GEMINI_API_KEY` | secret | API key for Google Gemini (get one at [aistudio.google.com](https://aistudio.google.com/apikey)) |
| `GEMINI_MODEL` | variable | Gemini model name (default: `gemini-2.5-flash`) |
| `ASTRO_CONTENT_DIR` | variable | Folder where the generated `.md` post is written (default: `content/blog`) |
| `ASTRO_ASSETS_DIR` | variable | Folder where staged images are copied (default: `public/images/blog`) |
| `JOURNEY_ID` | variable | Optional journey file ID, e.g. `2026-spain-morocco` (without `.md`) |
| `ASTRO_REPO_TOKEN` | secret | Fine-grained GitHub token limited to the Astro repository with `Contents: Read and write` for checkout and publishing |

Set `JOURNEY_ID` under **Settings → Secrets and variables → Actions → Repository variables** in `carlodaniele/nomad-pipeline-v2` (the source repository), not in `carlodaniele/astro-nomad-pipeline`. The poll workflow reads it once when staging each audio and stores the trimmed value in `media-input/<audio filename>.json`. Changing the variable later does not reassign staged audio. For manual audio pushes, stage a matching `.json` sidecar containing `{"journey_id":"2026-spain-morocco"}` before pushing the audio; without one, the article remains in the general blog. Blank values also omit `journey`.

Before Gemini generation, the Astro adapter checks a nonempty ID against `src/content/journeys/<ID>.md` in the Astro repository checked out with `ASTRO_REPO_TOKEN`. An invalid or unknown ID, or a failed checkout, stops the run before publishing. The generated post includes optional `journey` alongside `title`, `description`, `pubDate`, `tags`, and `heroImage` in its frontmatter. The publish step commits and pushes the Markdown and images in a single Astro repository commit.

With multiple images, the first becomes the hero image. The others are inserted in order at the end of successive `##` sections; any images beyond the number of sections are appended at the end of the post. If the article has no `##` sections, all additional images appear at the end.
The article body must begin with an introductory paragraph before its first heading. If the AI returns an empty body or starts with a heading, generation fails before the Markdown is published.

Kinsta only dispatches the GitHub Actions poll workflow; it does not run the polling script or the pipeline. No `JOURNEY_ID` or `GITHUB_VARIABLES_TOKEN` environment variable is needed on Kinsta. The workflows use the GitHub Actions `vars.JOURNEY_ID` context, not the GitHub REST API. If polling were moved to a Kinsta process in the future, that would require a dedicated token with `Actions: read` on the source repository to retrieve repository variables; the Astro publishing token should not be reused for that purpose.

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
   | `ASTRO_REPO_TOKEN`   | Fine-grained token for `carlodaniele/astro-nomad-pipeline` with `Contents: Read and write` (Astro adapter only) |

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
   | `JOURNEY_ID`                             | Optional Astro journey ID matching an existing `src/content/journeys/<ID>.md` (e.g. `2026-spain-morocco`) |

---

### 8 — Runtime workflows

- `Nomad Pipeline v2 Execution` (`pipeline.yml`) starts automatically on audio file push under `media-input/*` on branch `main`.
- Kinsta dispatches `Telegram Ingest Polling` (`telegram-poll.yml`) every 5 minutes; it can also run on demand. The workflow pulls new files from Telegram into `media-input/`.

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
