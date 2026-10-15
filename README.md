# School agent (Canvas + Outlook + Google Calendar via MCP)

Three small MCP servers that let Claude read your Canvas assignments/grades,
your Outlook mail/calendar, and your Google Calendar, so you can just ask
Claude Desktop things like "what's due this week and when am I free to do
it?" — no API keys for an LLM needed, since Claude Desktop is the brain.

Anyone can use this by cloning the repo and connecting their **own**
accounts — nothing is shared or hosted centrally, so there's no cost and no
app-review process to go through.

## 0. Install dependencies

```bash
cd school-agent-mcp
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 1. Canvas setup

1. In Canvas: **Account -> Settings -> New Access Token**. Copy it.
2. Copy `canvas_mcp/.env.example` to `canvas_mcp/.env` and fill in your
   Canvas URL and token.

## 2. Outlook (mail + calendar) setup

1. Go to https://portal.azure.com -> **Azure Active Directory -> App
   registrations -> New registration**.
   - Supported account types: "Accounts in any organizational directory and
     personal Microsoft accounts"
   - Redirect URI: leave blank
2. Copy the **Application (client) ID** from the Overview page.
3. Under **API permissions**, add (Microsoft Graph, Delegated):
   `Mail.Read`, `Calendars.Read`, `User.Read`
4. Copy `microsoft_mcp/.env.example` to `microsoft_mcp/.env` and paste in
   the client ID.
5. The first time the server runs, it will print a device code + a URL in
   its logs. Visit the URL, enter the code, sign in. After that, a
   `token_cache.json` is saved so you won't have to repeat this.

## 3. Google Calendar setup

1. Go to https://console.cloud.google.com -> create a project (free).
2. Enable the **Google Calendar API** (APIs & Services -> Library).
3. **APIs & Services -> Credentials -> Create Credentials -> OAuth client
   ID**, application type **Desktop app**. Download the JSON.
4. Save the downloaded file as `google_calendar_mcp/credentials.json`.
5. **APIs & Services -> OAuth consent screen -> Audience**, add your own
   Google account as a test user (required while unpublished — fine for
   personal use, still free).
6. First run opens a browser to sign in; a `token.json` is saved afterward.

## 4. Connect the servers to Claude Desktop

Open (or create) Claude Desktop's config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add each server (use the **full absolute path** to your venv's Python and
to each `server.py`):

```json
{
  "mcpServers": {
    "canvas": {
      "command": "/absolute/path/to/school-agent-mcp/venv/bin/python",
      "args": ["/absolute/path/to/school-agent-mcp/canvas_mcp/server.py"],
      "env": {
        "CANVAS_BASE_URL": "https://yourschool.instructure.com",
        "CANVAS_TOKEN": "your_token_here"
      }
    },
    "outlook": {
      "command": "/absolute/path/to/school-agent-mcp/venv/bin/python",
      "args": ["/absolute/path/to/school-agent-mcp/microsoft_mcp/server.py"],
      "env": {
        "MS_CLIENT_ID": "your_client_id_here"
      }
    },
    "google-calendar": {
      "command": "/absolute/path/to/school-agent-mcp/venv/bin/python",
      "args": ["/absolute/path/to/school-agent-mcp/google_calendar_mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop. You should see a small tools/plug icon indicating
the three servers are connected. Try asking:

> "What's on my Canvas to-do list, and do I have time this week to get it
> done based on my calendars?"

## 5. Optional: make it 24/7 and reachable from your phone (OpenClaw)

Claude Desktop only works while the app is open on your computer. If you
want a version that's always running and you can message from your phone,
swap in [OpenClaw](https://openclaw.ai) as the gateway instead — it's free,
open-source, and speaks MCP natively, so the same three servers plug in
without changes.

1. Install OpenClaw:
   ```bash
   curl -fsSL https://openclaw.ai/install.sh | bash
   ```
2. During setup, pick a free model provider (e.g. Groq — free tier, fast)
   and set up a messaging channel (Telegram is the quickest: message
   @BotFather on Telegram, create a bot, get a token, paste it into
   OpenClaw's setup).
3. Copy `openclaw_config_example.json`'s `mcp` section into your OpenClaw
   config (`~/.openclaw/openclaw.json` by default), filling in the same
   absolute paths and credentials you used for Claude Desktop.
4. Restart the gateway:
   ```bash
   openclaw gateway restart
   ```
5. Message your Telegram bot from your phone: "what's on my Canvas to-do
   list?" — it should call the same tools and answer, from anywhere.

**Where to run it for true 24/7 at $0:** your own computer works but has
to stay on. For a genuinely free always-on option, Oracle Cloud's free
tier includes an always-free small VM — install OpenClaw there instead of
locally, and it never has to sleep.

## Notes

- Each server is **read-only** on purpose (no send-email or delete tools) —
  safer to start with, and easy to extend once you trust the setup.
- If a tool call fails with an auth error, delete that server's cached
  token file (`token_cache.json` or `token.json`) and it will re-prompt you
  to sign in.
- Want this to also *proactively* email or message you a daily digest
  instead of only answering when asked? That needs a small scheduled
  script on top of this (cron / Task Scheduler) that calls Claude and
  sends the result somewhere — a natural next step once the servers here
  are working.
